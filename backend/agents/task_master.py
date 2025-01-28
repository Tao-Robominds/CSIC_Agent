from typing import Literal, TypedDict

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.store.base import BaseStore

import backend.agents.utils.configuration as configuration
from backend.agents.utils.update import update_command, update_todos, update_instructions
from backend.agents.prompts.task_master_prompts import MODEL_SYSTEM_MESSAGE
from backend.agents.utils.schemas import Command, ToDo
from backend.workflows.todo_panel_coordinator import TodoPanelCoordinator

from langchain_core.messages import HumanMessage

class UpdateMemory(TypedDict):
    """ Decision on what memory type to update """
    update_type: Literal['user', 'todo', 'instructions']

model = ChatOpenAI(model="gpt-4", temperature=0)

def task_master(state: MessagesState, config: RunnableConfig, store: BaseStore):
    """Load memories from the store and use them to personalize the chatbot's response."""
    
    # Get the user ID from the config
    configurable = configuration.Configuration.from_runnable_config(config)
    user_id = configurable.user_id

    # Retrieve command memory from the store
    namespace = ("command", user_id)
    memories = store.search(namespace)
    if memories:
        user_command = memories[0].value
    else:
        user_command = None

    # Retrieve people memory from the store
    namespace = ("todo", user_id)
    memories = store.search(namespace)
    todo = "\n".join(f"{mem.value}" for mem in memories)

    # Retrieve custom instructions
    namespace = ("instructions", user_id)
    memories = store.search(namespace)
    if memories:
        instructions = memories[0].value
    else:
        instructions = ""
    
    # Format the system message with current context
    system_msg = MODEL_SYSTEM_MESSAGE.format(
        user_command=user_command, 
        todo=todo, 
        instructions=instructions
    )

    # Respond using memory as well as the chat history
    response = model.bind_tools([UpdateMemory], parallel_tool_calls=False).invoke(
        [SystemMessage(content=system_msg)]+state["messages"]
    )

    return {"messages": [response]}

def route_message(state: MessagesState, config: RunnableConfig, store: BaseStore) -> Literal[END, "update_todos", "update_instructions", "update_command", "run_panel"]: # type: ignore
    """Reflect on the memories and chat history to decide whether to update the memory collection."""
    message = state['messages'][-1]
    if len(message.tool_calls) == 0:
        # Check if we should run panel discussions
        if isinstance(message, HumanMessage) and "run panel discussion" in message.content.lower():
            return "run_panel"
        return END
    else:
        tool_call = message.tool_calls[0]
        if tool_call['args']['update_type'] == "user":
            return "update_command"
        elif tool_call['args']['update_type'] == "todo":
            return "update_todos"
        elif tool_call['args']['update_type'] == "instructions":
            return "update_instructions"
        else:
            raise ValueError

# Add new node function for panel discussions
def run_panel_discussions(state: MessagesState, config: RunnableConfig, store: BaseStore):
    """Run panel discussions for relevant todos."""
    configurable = configuration.Configuration.from_runnable_config(config)
    user_id = configurable.user_id
    
    coordinator = TodoPanelCoordinator(store, user_id)
    results = coordinator.process_todos()
    
    # Format response message
    if not results:
        response = "No todos requiring panel discussions found."
    else:
        response = "Panel discussions completed:\n\n"
        for result in results:
            response += f"Task: {result['task']}\n"
            response += f"Participants: {result['participants']}\n"
            response += f"Summary: {result['summary']}\n\n"
    
    return {"messages": [AIMessage(content=response)]}


# Create the graph + all nodes
builder = StateGraph(MessagesState, config_schema=configuration.Configuration)

# Define the flow of the memory extraction process
builder.add_node("task_master", task_master)
builder.add_node(
    "update_todos", 
    lambda state, config, store: update_todos(state, config, store, model)
)
builder.add_node(
    "update_command", 
    lambda state, config, store: update_command(state, config, store, model)
)
builder.add_node(
    "update_instructions", 
    lambda state, config, store: update_instructions(state, config, store, model)
)
builder.add_node("run_panel", run_panel_discussions)

# Define the flow 
builder.add_edge(START, "task_master")
builder.add_conditional_edges("task_master", route_message)
builder.add_edge("update_todos", "task_master")
builder.add_edge("update_command", "task_master")
builder.add_edge("update_instructions", "task_master")
builder.add_edge("run_panel", END)

# Compile the graph
graph = builder.compile()