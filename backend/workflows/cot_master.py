from typing import Literal, TypedDict

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END

import backend.agents.utils.configuration as configuration
from backend.agents.csic_agent import CSICAgent
from backend.components.discussion_summarizer import DiscussionSummarizer
from backend.store.redis_store import RedisStore
from backend.store.redis_config import get_redis_config

# Initialize Redis store and model
redis_config = get_redis_config()
store = RedisStore(**redis_config)
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

REFLECTION_PROMPT = """You are an expert at analyzing complex discussions and identifying areas that need deeper exploration.
Your task is to:
1. Identify knowledge gaps in the current discussion
2. Point out assumptions that should be examined
3. Suggest specific areas that need more detailed analysis
4. Propose follow-up questions for the panel

Based on the discussion so far, what aspects need deeper investigation?"""

class MessagesState(TypedDict):
    messages: list

def run_panel_discussions(state: MessagesState, config: RunnableConfig):
    """Initialize panel discussion process by reformulating the query."""
    # Get the user's query
    query = state['messages'][-1].content
    
    # Prompt to reformulate the query
    reformulation_prompt = """You are an expert at breaking down questions into clear, researchable problems.
    Your task is to reformulate the given query into a clear problem statement that can be discussed by a panel of engineers.
    
    Please ensure the reformulation:
    1. Identifies the core technical question or challenge
    2. Frames it in a way that invites detailed technical discussion
    3. Makes any implicit assumptions explicit
    4. Is clear and actionable
    
    Original query: {query}
    
    Provide only the reformulated problem statement, without any additional explanation."""
    
    # Reformulate the query
    response = model.invoke([
        SystemMessage(content=reformulation_prompt.format(query=query)),
        HumanMessage(content=query)
    ])
    
    reformulated_query = response.content
    
    return {
        "messages": [
            AIMessage(content=f"Starting engineering panel discussion for the following problem:\n{reformulated_query}"),
            HumanMessage(content=reformulated_query)
        ]
    }

def run_project_manager(state: MessagesState, config: dict) -> MessagesState:
    """Handle Project Manager's response."""
    # Get just the latest message content as text
    current_query = state['messages'][-1].content if isinstance(state['messages'][-1], HumanMessage) else str(state['messages'][-1])
    
    try:
        agent = CSICAgent.create("PROJECT_MANAGER", "system", current_query)
        response = agent.actor()
        
        # Return updated state with new message
        return {
            "messages": state['messages'] + [f"Project Manager: {response}"]
        }
    except Exception as e:
        print(f"Project Manager Error: {str(e)}")
        return state

def run_senior_engineer(state: MessagesState, config: dict) -> MessagesState:
    """Handle Senior Engineer's response."""
    # Get just the latest message content as text
    current_query = state['messages'][-1].content if isinstance(state['messages'][-1], HumanMessage) else str(state['messages'][-1])
    
    try:
        agent = CSICAgent.create("SENIOR_ENGINEER", "system", current_query)
        response = agent.actor()
        
        # Return updated state with new message
        return {
            "messages": state['messages'] + [f"Senior Engineer: {response}"]
        }
    except Exception as e:
        print(f"Senior Engineer Error: {str(e)}")
        return state

def run_principal_engineer(state: MessagesState, config: dict) -> MessagesState:
    """Handle Principal Engineer's response."""
    # Get just the latest message content as text
    current_query = state['messages'][-1].content if isinstance(state['messages'][-1], HumanMessage) else str(state['messages'][-1])
    
    try:
        agent = CSICAgent.create("PRINCIPAL_ENGINEER", "system", current_query)
        response = agent.actor()
        
        # Return updated state with new message
        return {
            "messages": state['messages'] + [f"Principal Engineer: {response}"]
        }
    except Exception as e:
        print(f"Principal Engineer Error: {str(e)}")
        return state

def summarize_discussion(state: MessagesState, config: RunnableConfig):
    """Generate final summary of the panel discussion."""
    # Get the original inquiry
    inquiry = next((msg.content for msg in state['messages'] if isinstance(msg, HumanMessage)), "")
    
    # Collect all panel responses
    conversation_history = []
    for msg in state['messages']:
        if isinstance(msg, AIMessage):
            content = msg.content
            if any(role in content for role in ["Project Manager:", "Senior Engineer:", "Principal Engineer:"]):
                role = content.split(":")[0]
                conversation_history.append({
                    "role": role,
                    "content": content
                })
    
    summarizer = DiscussionSummarizer(inquiry, conversation_history)
    summary = summarizer.generate_summary()
    
    return {"messages": state['messages'] + [AIMessage(content=f"\nFinal Summary:\n{summary}")]}

def reflect_on_summary(state: MessagesState, config: RunnableConfig):
    """Reflect on the summary and identify if further discussion is needed."""
    # Get the latest summary
    summary = next((msg.content for msg in reversed(state['messages']) 
                   if isinstance(msg, AIMessage) and "Final Summary:" in msg.content), "")
    
    reflection_prompt = """You are an expert at analyzing engineering discussions and their conclusions.
    Your task is to:
    1. Analyze the completeness of the solution
    2. Identify any unexplored technical aspects
    3. Suggest specific areas that need further engineering input
    4. Determine if another round of discussion would be valuable
    
    If you find significant gaps or areas needing more discussion, clearly state what specific aspects the panel should address.
    If the solution is comprehensive, acknowledge its completeness."""
    
    response = model.invoke([
        SystemMessage(content=reflection_prompt),
        HumanMessage(content=f"Summary to analyze:\n{summary}")
    ])
    
    reflection = response.content
    
    # If reflection suggests more discussion is needed
    if any(phrase in reflection.lower() for phrase in ["should discuss", "need more input", "further exploration", "not addressed"]):
        return {
            "messages": state['messages'] + [
                AIMessage(content=f"\nReflection on Summary:\n{reflection}"),
                HumanMessage(content="Let's explore these aspects with our engineering panel.")
            ]
        }
    
    # If the solution is comprehensive
    return {
        "messages": state['messages'] + [
            AIMessage(content=f"\nFinal Reflection:\n{reflection}")
        ]
    }

def route_summary_reflection(state: MessagesState, config: RunnableConfig) -> Literal["run_panel", END]: # type: ignore
    """Route based on the reflection on summary."""
    last_messages = state['messages'][-2:]  # Get last two messages
    
    for message in last_messages:
        if isinstance(message, HumanMessage) and "explore" in message.content.lower():
            return "run_panel"  # Start another round of panel discussion
    
    return END

# Create the graph
builder = StateGraph(MessagesState, config_schema=configuration.Configuration)

# Add nodes
builder.add_node("run_panel", run_panel_discussions)
builder.add_node("project_manager_response", run_project_manager)
builder.add_node("senior_engineer_response", run_senior_engineer)
builder.add_node("principal_engineer_response", run_principal_engineer)
builder.add_node("summarize_panel", summarize_discussion)
builder.add_node("reflect_summary", reflect_on_summary)

# Define the flow
builder.add_edge(START, "run_panel")
# Panel members respond after query reformulation
builder.add_edge("run_panel", "project_manager_response")
builder.add_edge("run_panel", "senior_engineer_response")
builder.add_edge("run_panel", "principal_engineer_response")
# All responses go directly to summary
builder.add_edge("project_manager_response", "summarize_panel")
builder.add_edge("senior_engineer_response", "summarize_panel")
builder.add_edge("principal_engineer_response", "summarize_panel")
# Summary goes to reflection
builder.add_edge("summarize_panel", "reflect_summary")
# Reflection can either loop back to panel or end
builder.add_conditional_edges("reflect_summary", route_summary_reflection)

# Compile the graph
graph = builder.compile() 