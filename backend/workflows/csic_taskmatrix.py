from typing import Literal, TypedDict
import json

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END

import backend.agents.utils.configuration as configuration
from backend.agents.csic_agent import CSICAgent
from backend.agents.csic_panel_admin import PanelAdminAgent
from backend.agents.evaluator_agent import EvaluatorAgent
from backend.components.discussion_summarizer import DiscussionSummarizer
from langchain_core.messages import HumanMessage

model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

def run_panel_discussions(state: MessagesState, config: RunnableConfig):
    """Initialize panel discussion process."""
    inquiry = state['messages'][-1].content
    
    return {
        "messages": [
            AIMessage(content=f"Panel discussion:\n{inquiry}"),
            HumanMessage(content=inquiry)
        ]
    }

def run_panel_admin(state: MessagesState, config: RunnableConfig):
    """Handle panel admin selection of participants."""
    admin = PanelAdminAgent(user_id="CSIC", request=state['messages'][-1].content)
    response = admin.actor()
    
    try:
        panel_info = json.loads(response)
        formatted_response = (
            f"Panel Discussion Setup:\n\n"
            f"Selected Participants: {', '.join(panel_info.get('invited', []))}\n"
            f"Inquiry: {panel_info.get('inquiry', '')}\n"
            f"Suggestions: {panel_info.get('suggestions', '')}"
        )
    except (json.JSONDecodeError, TypeError) as e:
        formatted_response = f"Error: {str(e)}\nResponse: {response}"
        
    return {
        "messages": [AIMessage(content=formatted_response)]
    }

def run_project_manager(state: MessagesState, config: RunnableConfig):
    """Handle Project Manager's response."""
    agent = CSICAgent.create("PROJECT_MANAGER", "CSIC", state['messages'][-1].content)
    response = agent.actor()
    
    return {
        "messages": [AIMessage(content=f"Project Manager: {response}")]
    }

def run_senior_engineer(state: MessagesState, config: RunnableConfig):
    """Handle Senior Engineer's response."""
    agent = CSICAgent.create("SENIOR_ENGINEER", "CSIC", state['messages'][-1].content)
    response = agent.actor()
    
    return {
        "messages": [AIMessage(content=f"Senior Engineer: {response}")]
    }

def run_principal_engineer(state: MessagesState, config: RunnableConfig):
    """Handle Principal Engineer's response."""
    agent = CSICAgent.create("PRINCIPAL_ENGINEER", "CSIC", state['messages'][-1].content)
    response = agent.actor()
    
    return {
        "messages": [AIMessage(content=f"Principal Engineer: {response}")]
    }

def summarize_discussion(state: MessagesState, config: RunnableConfig):
    messages = state['messages']
    
    # Get the original inquiry
    inquiry = next((msg.content for msg in messages if isinstance(msg, HumanMessage)), "")
    
    # Wait for all executive responses
    exec_responses = {
        "PROJECT_MANAGER": None,
        "SENIOR_ENGINEER": None,
        "PRINCIPAL_ENGINEER": None
    }
    
    for msg in messages:
        if isinstance(msg, AIMessage):
            content = msg.content
            # Match responses to executives
            if content.startswith("PROJECT_MANAGER:"):
                exec_responses["PROJECT_MANAGER"] = content
            elif content.startswith("SENIOR_ENGINEER:"):
                exec_responses["SENIOR_ENGINEER"] = content
            elif content.startswith("PRINCIPAL_ENGINEER:"):
                exec_responses["PRINCIPAL_ENGINEER"] = content
    
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

    # Get the original task/inquiry
    inquiry = next((msg.content for msg in messages if isinstance(msg, HumanMessage)), "")
    
    # Get the summary from the last non-key AIMessage
    summary = next((msg.content for msg in reversed(messages) 
                   if isinstance(msg, AIMessage) 
                   and not msg.content.startswith("Starting panel discussion")), "")
    
    # Create evaluator agent
    evaluator = EvaluatorAgent.create("CSIC", inquiry, summary)
    
    # Get evaluation results
    evaluation = evaluator.actor()
    
    # Force re-evaluation for any of these conditions
    if "recommend" not in summary.lower() or "action" not in summary.lower():
        return {
            "messages": [
                AIMessage(content=f"Summary needs improvement: Missing key components or insufficient detail. Restarting panel discussion.")
            ]
        }
    
    return {
        "messages": [
            AIMessage(content="Summary evaluation passed all criteria.")
        ]
    }

def route_after_evaluation(state: MessagesState, config: RunnableConfig) -> Literal["panel_admin", END]: # type: ignore
    """Route based on evaluation results."""
    message = state['messages'][-1]
    if not isinstance(message, AIMessage):
        return END
        
    # If the message contains "needs improvement", route back to panel_admin
    if "needs improvement" in message.content:
        return "panel_admin"
    elif "Summary evaluation passed" in message.content:
        return END
    return END

# Create the graph + all nodes
builder = StateGraph(MessagesState, config_schema=configuration.Configuration)

# Add all nodes first
builder.add_node("run_panel", run_panel_discussions)
builder.add_node("panel_admin", run_panel_admin)
builder.add_node("project_manager_response", run_project_manager)
builder.add_node("senior_engineer_response", run_senior_engineer)
builder.add_node("principal_engineer_response", run_principal_engineer)
builder.add_node("summarize_panel", summarize_discussion)
builder.add_node("evaluate_summary", evaluate_summary)

# Define the flow - go directly to run_panel
builder.add_edge(START, "run_panel")

# Define panel discussion flow
builder.add_edge("run_panel", "panel_admin")

# All responses follow panel_admin
builder.add_edge("panel_admin", "project_manager_response")
builder.add_edge("panel_admin", "senior_engineer_response")
builder.add_edge("panel_admin", "principal_engineer_response")

# All responses go to summarize_panel
builder.add_edge("project_manager_response", "summarize_panel")
builder.add_edge("senior_engineer_response", "summarize_panel")
builder.add_edge("principal_engineer_response", "summarize_panel")

# Final evaluation flow
builder.add_edge("summarize_panel", "evaluate_summary")
builder.add_conditional_edges("evaluate_summary", route_after_evaluation)

# Compile the graph
graph = builder.compile()