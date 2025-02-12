from typing import Literal, TypedDict

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.store.base import BaseStore

import backend.agents.utils.configuration as configuration
from backend.agents.utils.update import update_todos, update_instructions
from backend.agents.prompts.panel_master_prompts import MODEL_SYSTEM_MESSAGE
from backend.agents.utils.schemas import ToDo
from backend.agents.c_agent import CAgent
from backend.agents.panel_admin import PanelAdminAgent
from backend.components.discussion_summarizer import DiscussionSummarizer
from langchain_core.messages import HumanMessage
from backend.store.redis_store import RedisStore
from backend.store.redis_config import get_redis_config

# Initialize Redis store
redis_config = get_redis_config()
store = RedisStore(**redis_config)

class UpdateMemory(TypedDict):
    """ Decision on what memory type to update """
    update_type: Literal['todo', 'instructions']

model = ChatOpenAI(model="gpt-4o", temperature=0)

def panel_master(state: MessagesState, config: RunnableConfig):
    """Load memories from the store and use them to personalize the chatbot's response."""
    
    # Check for panel discussion request first
    message = state['messages'][-1]
    if isinstance(message, HumanMessage):
        msg_lower = message.content.lower()
        if "run panel discussion" in msg_lower:
            configurable = configuration.Configuration.from_runnable_config(config)
            user_id = configurable.user_id
            
            namespace = ("todo", user_id)
            todos = store.search(namespace)
            active_todos = [todo for todo in todos if todo.value.get('status') != 'Done']
            
            if not active_todos:
                return {"messages": [AIMessage(content="No active todos found. Please add a todo item first.")]}
            
            return {"messages": []}  # Return empty response to let routing handle it
    
    # Get the user ID from the config
    configurable = configuration.Configuration.from_runnable_config(config)
    user_id = configurable.user_id

    # Retrieve todo items
    namespace = ("todo", user_id)
    memories = store.search(namespace)
    todo = "\n".join(f"{mem.value}" for mem in memories)

    # Retrieve custom instructions
    namespace = ("instructions", user_id)
    memories = store.search(namespace)
    instructions = memories[0].value if memories else ""
    
    # Format the system message with current context
    system_msg = MODEL_SYSTEM_MESSAGE.format(
        todo=todo, 
        instructions=instructions
    )

    # Respond using memory and chat history
    response = model.bind_tools([UpdateMemory], parallel_tool_calls=False).invoke(
        [SystemMessage(content=system_msg)]+state["messages"]
    )

    return {"messages": [response]}

def route_message(state: MessagesState, config: RunnableConfig) -> Literal[END, "update_todos", "update_instructions", "run_panel"]: # type: ignore
    """Route messages to appropriate handlers."""
    message = state['messages'][-1]
    
    if isinstance(message, HumanMessage):
        msg_lower = message.content.lower()
        if "run panel discussion" in msg_lower:
            return "run_panel"
    
    if len(message.tool_calls) == 0:
        return END
    else:
        tool_call = message.tool_calls[0]
        if tool_call['args']['update_type'] == "todo":
            return "update_todos"
        elif tool_call['args']['update_type'] == "instructions":
            return "update_instructions"
        else:
            return END

# Add new node function for panel discussions
def run_panel_discussions(state: MessagesState, config: RunnableConfig):
    """Initialize panel discussion process."""
    # Get the user ID from the config
    configurable = configuration.Configuration.from_runnable_config(config)
    user_id = configurable.user_id
    
    # Get active todos
    namespace = ("todo", user_id)
    todos = store.search(namespace)
    active_todos = [todo for todo in todos if todo.value.get('status') != 'Done']
    
    if not active_todos:
        return {"messages": [AIMessage(content="No active todos found. Please add a todo item first.")]}
    
    # Get the command text to check if a specific todo number was requested
    command = state['messages'][-1].content.lower()
    selected_index = None
    
    # Check if a specific todo number was mentioned
    for i in range(len(active_todos)):
        if f"run panel discussion {i+1}" in command:
            selected_index = i
            break
    
    # If no specific todo was requested, use the first one
    if selected_index is None:
        selected_index = 0
    
    selected_todo = active_todos[selected_index]
    inquiry = selected_todo.value.get('task', '')
    
    # Store the selected todo key in the messages for later use
    return {
        "messages": [
            AIMessage(content=f"Selected todo key: {selected_todo.key}"),
            AIMessage(content=f"Starting panel discussion for todo:\n{inquiry}"),
            HumanMessage(content=inquiry)
        ]
    }

def route_after_ceo(state: MessagesState, config: RunnableConfig) -> str:
    """Route to next node based on CEO's response dependencies."""
    # Get the last message which should contain CEO's response
    ceo_response = state['messages'][-1].content
    
    # Analyze dependencies in CEO's response
    if "financial" in ceo_response.lower() or "budget" in ceo_response.lower():
        return "cfo_response"
    elif "marketing" in ceo_response.lower() or "market" in ceo_response.lower():
        return "cmo_response"
    return "summarize_panel"

def route_after_cfo(state: MessagesState, config: RunnableConfig) -> str:
    """Route to next node based on CFO's response dependencies."""
    # Get the last message which should contain CFO's response
    cfo_response = state['messages'][-1].content
    
    if "marketing" in cfo_response.lower() or "market" in cfo_response.lower():
        return "cmo_response"
    return "summarize_panel"

def run_panel_admin(state: MessagesState, config: RunnableConfig):
    """Handle panel admin selection of participants."""
    admin = PanelAdminAgent(user_id="system", request=state['messages'][-1].content)
    response = admin.actor()
    
    # Format the response for better readability
    try:
        import json
        panel_info = json.loads(response)
        formatted_response = (
            f"Panel Discussion Setup:\n\n"
            f"Context: {panel_info['context']}\n\n"
            f"Selected Participants: {', '.join(panel_info['selected_participants'])}\n\n"
            f"Instructions: {panel_info['instructions']}"
        )
    except json.JSONDecodeError:
        # Fallback in case response is not valid JSON
        formatted_response = response
        
    return {"messages": [AIMessage(content=formatted_response)]}

def run_ceo(state: MessagesState, config: RunnableConfig):
    """Handle CEO's response."""
    agent = CAgent.create("CEO", "system", state['messages'][-1].content)
    response = agent.actor()
    return {"messages": [AIMessage(content=f"CEO: {response}")]}

def run_cfo(state: MessagesState, config: RunnableConfig):
    """Handle CFO's response."""
    context = "\n".join([msg.content for msg in state['messages'] if isinstance(msg, AIMessage)])
    request = f"{state['messages'][-1].content}\n\nPrevious discussion:\n{context}"
    
    agent = CAgent.create("CFO", "system", request)
    response = agent.actor()
    return {"messages": [AIMessage(content=f"CFO: {response}")]}

def run_cmo(state: MessagesState, config: RunnableConfig):
    """Handle CMO's response."""
    context = "\n".join([msg.content for msg in state['messages'] if isinstance(msg, AIMessage)])
    request = f"{state['messages'][-1].content}\n\nPrevious discussion:\n{context}"
    
    agent = CAgent.create("CMO", "system", request)
    response = agent.actor()
    return {"messages": [AIMessage(content=f"CMO: {response}")]}

def summarize_discussion(state: MessagesState, config: RunnableConfig):
    # Get the selected todo key from the first message
    messages = state['messages']
    selected_todo_key = None
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.content.startswith("Selected todo key:"):
            selected_todo_key = msg.content.split(": ")[1].strip()
            break
    
    # Get the original inquiry
    inquiry = next((msg.content for msg in messages if isinstance(msg, HumanMessage)), "")
    
    # Wait for all executive responses
    exec_responses = {
        "CEO": None,
        "CFO": None,
        "CMO": None
    }
    
    for msg in messages:
        if isinstance(msg, AIMessage):
            content = msg.content
            # Match responses to executives
            if content.startswith("CEO:"):
                exec_responses["CEO"] = content
            elif content.startswith("CFO:"):
                exec_responses["CFO"] = content
            elif content.startswith("CMO:"):
                exec_responses["CMO"] = content
    
    # Only proceed if we have all responses
    if all(exec_responses.values()):
        conversation_history = []
        for role, content in exec_responses.items():
            if not content.startswith("Selected todo key:"):  # Skip the key message
                conversation_history.append({
                    "role": role,
                    "content": content
                })
        
        summarizer = DiscussionSummarizer(inquiry, conversation_history)
        summary = summarizer.generate_summary()
        
        # Get the user ID from the config and update the todo item
        configurable = configuration.Configuration.from_runnable_config(config)
        user_id = configurable.user_id
        namespace = ("todo", user_id)
        
        # Update the todo with the summary and mark as done
        if selected_todo_key:
            todo = store.get(namespace, selected_todo_key)
            if todo:
                updated_todo = {
                    **todo.value,
                    'status': 'Done',
                    'solution': summary
                }
                store.put(namespace, selected_todo_key, updated_todo)
        
        return {"messages": [AIMessage(content=f"\n\n{summary}")]}
    else:
        missing = [role for role, resp in exec_responses.items() if resp is None]
        return {"messages": [AIMessage(content=f"⏳ Waiting for responses from: {', '.join(missing)}")]}

# Create the graph + all nodes
builder = StateGraph(MessagesState, config_schema=configuration.Configuration)

# Define the simplified flow
builder.add_node("panel_master", panel_master)
builder.add_node(
    "update_todos", 
    lambda state, config: update_todos(state, config, store, model)
)
builder.add_node(
    "update_instructions", 
    lambda state, config: update_instructions(state, config, store, model)
)

# Add panel discussion nodes
builder.add_node("run_panel", lambda state, config: run_panel_discussions(state, config))
builder.add_node("panel_admin", lambda state, config: run_panel_admin(state, config))
builder.add_node("ceo_response", lambda state, config: run_ceo(state, config))
builder.add_node("cfo_response", lambda state, config: run_cfo(state, config))
builder.add_node("cmo_response", lambda state, config: run_cmo(state, config))
builder.add_node("summarize_panel", lambda state, config: summarize_discussion(state, config))

# Define the main flow
builder.add_edge(START, "panel_master")
builder.add_conditional_edges("panel_master", route_message)
builder.add_edge("update_todos", "panel_master")
builder.add_edge("update_instructions", "panel_master")

# Define panel discussion flow
builder.add_edge("run_panel", "panel_admin")
# After panel_admin, branch out to all executives
builder.add_edge("panel_admin", "ceo_response")
builder.add_edge("panel_admin", "cfo_response")
builder.add_edge("panel_admin", "cmo_response")
# All executive responses go to summarize
builder.add_edge("ceo_response", "summarize_panel")
builder.add_edge("cfo_response", "summarize_panel")
builder.add_edge("cmo_response", "summarize_panel")
builder.add_edge("summarize_panel", END)

# Compile the graph
graph = builder.compile()