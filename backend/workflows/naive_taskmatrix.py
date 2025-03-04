from typing import Literal, Dict, List
import json

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END

import backend.agents.utils.configuration as configuration
from backend.agents.project_manager_agent import ProjectManagerAgent
from backend.agents.principal_engineer_agent import PrincipalEngineerAgent
from backend.agents.senior_engineer_agent import SeniorEngineerAgent
from backend.agents.summarizer_agent import SummarizerAgent
from backend.agents.evaluator_agent import EvaluatorAgent

model = ChatOpenAI(model="gpt-4o", temperature=0.3)

def run_panel_discussions(state: MessagesState, config: RunnableConfig):
    """Initialize panel discussion process."""
    inquiry = state['messages'][-1].content
    
    return {
        "messages": [
            AIMessage(content=f"Panel discussion: Islington Tunnel Inspection Strategy\n\nTask: {inquiry}"),
            HumanMessage(content=inquiry)
        ]
    }

def run_project_manager(state: MessagesState, config: RunnableConfig):
    """Handle Project Manager's response in the tunnel inspection scenario."""
    inquiry = state['messages'][-1].content
    agent = ProjectManagerAgent(user_id="CSIC", task=inquiry)
    response = agent.actor()
    
    return {
        "messages": [AIMessage(content=response["response"])]
    }

def run_senior_engineer(state: MessagesState, config: RunnableConfig):
    """Handle Senior Engineer's response in the tunnel inspection scenario."""
    inquiry = state['messages'][-1].content
    agent = SeniorEngineerAgent(user_id="CSIC", task=inquiry)
    response = agent.actor()
    
    return {
        "messages": [AIMessage(content=response["response"])]
    }

def run_principal_engineer(state: MessagesState, config: RunnableConfig):
    """Handle Principal Engineer's response in the tunnel inspection scenario."""
    inquiry = state['messages'][-1].content
    agent = PrincipalEngineerAgent(user_id="CSIC", task=inquiry)
    response = agent.actor()
    
    return {
        "messages": [AIMessage(content=response["response"])]
    }

def summarize_discussion(state: MessagesState, config: RunnableConfig):
    """Summarize the panel discussion using the SummarizerAgent."""
    messages = state['messages']
    
    # Get the original inquiry
    inquiry = next((msg.content for msg in messages if isinstance(msg, HumanMessage)), "")
    
    # Collect all agent responses
    discussion = []
    
    for i, msg in enumerate(messages):
        if isinstance(msg, AIMessage) and i > 0:  # Skip the initial panel discussion message
            # Determine agent type based on content patterns or message position
            agent_type = "unknown"
            # Simplified agent type detection based on message order
            if i == 2:  # First response is from Project Manager
                agent_type = "project_manager"
            elif i == 3:  # Second response is from Senior Engineer
                agent_type = "senior_engineer"
            elif i == 4:  # Third response is from Principal Engineer
                agent_type = "principal_engineer"
                
            discussion.append({
                "agent_type": agent_type,
                "response": msg.content
            })
    
    # Only proceed if we have all expected responses
    if len(discussion) >= 3:
        summarizer = SummarizerAgent(user_id="CSIC", discussion=discussion)
        summary = summarizer.actor()
        
        return {
            "messages": [
                AIMessage(content=f"\n\nSummary of Panel Discussion:\n\n{summary['summary']}")
            ]
        }
    else:
        # If we don't have all responses yet, indicate we're waiting
        return {
            "messages": [
                AIMessage(content=f"⏳ Waiting for all participants to respond. Current response count: {len(discussion)}/3")
            ]
        }

def evaluate_summary(state: MessagesState, config: RunnableConfig):
    """Evaluate the panel discussion summary using the EvaluatorAgent."""
    messages = state['messages']

    # Get the original task/inquiry
    inquiry = next((msg.content for msg in messages if isinstance(msg, HumanMessage)), "")
    
    # Get the summary from the last non-waiting AIMessage
    summary = next((msg.content for msg in reversed(messages) 
                   if isinstance(msg, AIMessage) 
                   and not msg.content.startswith("⏳")), "")
    
    # Extract just the summary part if it includes the header
    if "Summary of Panel Discussion:" in summary:
        summary = summary.split("Summary of Panel Discussion:", 1)[1].strip()
    
    # Create evaluator agent
    evaluator = EvaluatorAgent(user_id="CSIC", task=inquiry, summary=summary)
    
    # Get evaluation results
    evaluation = evaluator.actor()
    
    # Format the evaluation results for display
    result = f"Summary Evaluation:\n\n"
    
    if evaluation["passes"]:
        result += "✅ The summary passes all evaluation criteria.\n\n"
    else:
        result += "❌ The summary needs improvement in the following areas:\n\n"
        
        criteria = evaluation["criteria"]
        for criterion, passes in [
            ("Completeness", criteria.completeness),
            ("Actionability", criteria.actionability),
            ("Clarity", criteria.clarity),
            ("Stakeholder Alignment", criteria.stakeholder_alignment),
            ("Feasibility", criteria.feasibility)
        ]:
            icon = "✅" if passes else "❌"
            result += f"{icon} {criterion}\n"
        
        result += "\nImprovement Suggestions:\n"
        for suggestion in evaluation["suggestions"]:
            result += f"- {suggestion}\n"
    
    return {
        "messages": [
            AIMessage(content=result)
        ]
    }

def route_after_evaluation(state: MessagesState, config: RunnableConfig) -> Literal["run_panel_discussions", END]: # type: ignore
    """Route based on evaluation results."""
    message = state['messages'][-1]
    if not isinstance(message, AIMessage):
        return END
        
    # If the message contains "needs improvement", route back to beginning
    if "needs improvement" in message.content:
        return "run_panel_discussions"
    else:
        return END

# Create the graph + all nodes
builder = StateGraph(MessagesState)

# Add all nodes first
builder.add_node("run_panel_discussions", run_panel_discussions)
builder.add_node("project_manager_response", run_project_manager)
builder.add_node("senior_engineer_response", run_senior_engineer)
builder.add_node("principal_engineer_response", run_principal_engineer)
builder.add_node("summarize_discussion", summarize_discussion)
builder.add_node("evaluate_summary", evaluate_summary)

# Define the flow
builder.add_edge(START, "run_panel_discussions")

# All responses follow panel discussion setup
builder.add_edge("run_panel_discussions", "project_manager_response")
builder.add_edge("run_panel_discussions", "senior_engineer_response")
builder.add_edge("run_panel_discussions", "principal_engineer_response")

# All responses go to summarize_discussion
builder.add_edge("project_manager_response", "summarize_discussion")
builder.add_edge("senior_engineer_response", "summarize_discussion")
builder.add_edge("principal_engineer_response", "summarize_discussion")

# Final evaluation flow
builder.add_edge("summarize_discussion", "evaluate_summary")
builder.add_conditional_edges("evaluate_summary", route_after_evaluation)

# Compile the graph
graph = builder.compile() 