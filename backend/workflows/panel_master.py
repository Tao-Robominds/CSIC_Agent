from typing import Literal, TypedDict

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.store.base import BaseStore

import backend.agents.utils.configuration as configuration
from backend.agents.prompts.panel_master_prompts import MODEL_SYSTEM_MESSAGE
from backend.agents.c_agent import CAgent
from backend.agents.panel_admin import PanelAdminAgent
from backend.agents.evaluator_agent import EvaluatorAgent
from backend.components.discussion_summarizer import DiscussionSummarizer
from langchain_core.messages import HumanMessage

model = ChatOpenAI(model="gpt-4", temperature=0)

def run_panel_discussions(state: MessagesState, config: RunnableConfig):
    """Initialize panel discussion process."""
    # Get the inquiry from the last human message
    inquiry = state['messages'][-1].content
    
    return {
        "messages": [
            AIMessage(content=f"Starting panel discussion for inquiry:\n{inquiry}"),
            HumanMessage(content=inquiry)
        ]
    }

def run_panel_admin(state: MessagesState, config: RunnableConfig):
    """Handle panel admin selection of participants."""
    admin = PanelAdminAgent(user_id="system", request=state['messages'][-1].content)
    response = admin.actor()
    
    # Format the response for better readability
    try:
        import json
        # Add null check before parsing
        if not response:
            return {"messages": [AIMessage(content="Error: No response received from Panel Admin")]}
        
        # Clean up the response by replacing semicolons with commas
        cleaned_response = response.replace(";", ",")
        panel_info = json.loads(cleaned_response)
        
        # Extract the relevant information
        formatted_response = (
            f"Panel Discussion Setup:\n\n"
            f"Timestamp: {panel_info.get('timestamp', 'Not specified')}\n"
            f"Selected Participants: {', '.join(panel_info.get('invited', []))}\n"
            f"Inquiry: {panel_info.get('inquiry', 'Not specified')}\n"
        )
    except (json.JSONDecodeError, TypeError) as e:
        # Improved error handling with original response
        formatted_response = (
            f"Error processing panel admin response: {str(e)}\n"
            f"Raw response: {response}\n"
            "Please check the panel admin's response format."
        )
        
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
    messages = state['messages']
    
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
            conversation_history.append({
                "role": role,
                "content": content
            })
        
        summarizer = DiscussionSummarizer(inquiry, conversation_history)
        summary = summarizer.generate_summary()
        
        return {
            "messages": [
                AIMessage(content=f"\n\n{summary}")
            ]
        }
    else:
        missing = [role for role, resp in exec_responses.items() if resp is None]
        return {"messages": [AIMessage(content=f"⏳ Waiting for responses from: {', '.join(missing)}")]}

def evaluate_summary(state: MessagesState, config: RunnableConfig):
    """Evaluate the panel discussion summary."""
    messages = state['messages']
    
    # Get or initialize the loop counter
    loop_count = state.get("loop_count", 0)
    
    # Check if we've exceeded maximum loops (e.g., 3 attempts)
    MAX_LOOPS = 3
    if loop_count >= MAX_LOOPS:
        return {
            "messages": [
                AIMessage(content="⚠️ Maximum iteration limit reached. Final summary:\n\n" + 
                         next((msg.content for msg in reversed(messages) 
                              if isinstance(msg, AIMessage) 
                              and not msg.content.startswith("Starting panel discussion")), ""))
            ]
        }
    
    # Increment loop counter
    state["loop_count"] = loop_count + 1
    
    # Get the original task/inquiry
    inquiry = next((msg.content for msg in messages if isinstance(msg, HumanMessage)), "")
    
    # Get the summary from the last non-key AIMessage
    summary = next((msg.content for msg in reversed(messages) 
                   if isinstance(msg, AIMessage) 
                   and not msg.content.startswith("Starting panel discussion")), "")
    
    # Force re-evaluation if we don't have all executive responses
    exec_responses = {
        "CEO": False,
        "CFO": False,
        "CMO": False
    }
    
    for msg in messages:
        if isinstance(msg, AIMessage):
            content = msg.content
            if content.startswith("CEO:"):
                exec_responses["CEO"] = True
            elif content.startswith("CFO:"):
                exec_responses["CFO"] = True
            elif content.startswith("CMO:"):
                exec_responses["CMO"] = True
    
    # If we're missing any executive responses, immediately return for re-evaluation
    if not all(exec_responses.values()):
        missing = [role for role, present in exec_responses.items() if not present]
        return {
            "messages": [
                AIMessage(content=f"⚠️ Summary needs improvement (Attempt {loop_count + 1}/{MAX_LOOPS}): Missing responses from {', '.join(missing)}. Restarting panel discussion.")
            ]
        }
    
    # Create evaluator agent
    configurable = configuration.Configuration.from_runnable_config(config)
    user_id = configurable.user_id
    evaluator = EvaluatorAgent.create(user_id, inquiry, summary)
    
    # Get evaluation results
    evaluation = evaluator.actor()
    
    # Force re-evaluation for any of these conditions
    if (len(summary.split()) < 50 or  # Too short
        "CEO" not in summary or      # Missing CEO perspective
        "CFO" not in summary or      # Missing CFO perspective
        "CMO" not in summary or      # Missing CMO perspective
        "recommend" not in summary.lower() or  # No clear recommendation
        "action" not in summary.lower()):     # No clear action items
        
        return {
            "messages": [
                AIMessage(content=f"⚠️ Summary needs improvement (Attempt {loop_count + 1}/{MAX_LOOPS}): Missing key components or insufficient detail. Restarting panel discussion.")
            ]
        }
    
    # If we made it here, the summary passed all checks
    return {
        "messages": [
            AIMessage(content="✅ Summary evaluation passed all criteria.")
        ]
    }

def route_after_evaluation(state: MessagesState, config: RunnableConfig) -> Literal["panel_admin", END]:
    """Route based on evaluation results."""
    message = state['messages'][-1]
    if not isinstance(message, AIMessage):
        return END
        
    # If the message contains "needs improvement", route back to panel_admin
    if "needs improvement" in message.content:
        return "panel_admin"
    # If the message indicates success, end the workflow
    elif "✅ Summary evaluation passed" in message.content:
        return END
    # Default case - end the workflow
    return END

# Create the graph + all nodes
builder = StateGraph(MessagesState, config_schema=configuration.Configuration)

# Add all nodes first
builder.add_node("run_panel", run_panel_discussions)
builder.add_node("panel_admin", run_panel_admin)
builder.add_node("ceo_response", run_ceo)
builder.add_node("cfo_response", run_cfo)
builder.add_node("cmo_response", run_cmo)
builder.add_node("summarize_panel", summarize_discussion)
builder.add_node("evaluate_summary", evaluate_summary)

# Define the flow - go directly to run_panel
builder.add_edge(START, "run_panel")

# Define panel discussion flow
builder.add_edge("run_panel", "panel_admin")

# All responses follow panel_admin
builder.add_edge("panel_admin", "ceo_response")
builder.add_edge("panel_admin", "cfo_response")
builder.add_edge("panel_admin", "cmo_response")

# All responses go to summarize_panel
builder.add_edge("ceo_response", "summarize_panel")
builder.add_edge("cfo_response", "summarize_panel")
builder.add_edge("cmo_response", "summarize_panel")

# Final evaluation flow
builder.add_edge("summarize_panel", "evaluate_summary")
builder.add_conditional_edges("evaluate_summary", route_after_evaluation)

# Compile the graph
graph = builder.compile()