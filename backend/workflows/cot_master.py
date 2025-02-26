from typing import Literal, TypedDict
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

import backend.agents.utils.configuration as configuration
from backend.agents.csic_agent import CSICAgent

# Initialize model
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

class MessagesState(TypedDict):
    message: str

def run_panel_discussions(state: MessagesState, config: RunnableConfig):
    """Initialize panel discussion process by reformulating the query."""
    # Get the user's query as plain text
    query = state['message']
    
    # Prompt to reformulate the query
    reformulation_prompt = """You are an expert at breaking down questions into clear, researchable problems.
    Your task is to reformulate the given query into a clear problem statement that can be discussed by a panel of engineers.
    
    Please ensure the reformulation:
    1. Identifies the core question or challenge
    2. Frames it in a way that invites detailed discussion
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
        "message": reformulated_query
    }

def run_project_manager(state: MessagesState, config: dict) -> MessagesState:
    """Handle Project Manager's response."""
    query = state['message']
    
    try:
        agent = CSICAgent.create("PROJECT_MANAGER", "system", query)
        response = agent.actor()
        return {
            "message": f"Project Manager: {response}"
        }
    except Exception as e:
        print(f"Project Manager Error: {str(e)}")
        return state

def run_senior_engineer(state: MessagesState, config: dict) -> MessagesState:
    """Handle Senior Engineer's response."""
    query = state['message']
    
    try:
        agent = CSICAgent.create("SENIOR_ENGINEER", "system", query)
        response = agent.actor()
        return {
            "message": f"Senior Engineer: {response}"
        }
    except Exception as e:
        print(f"Senior Engineer Error: {str(e)}")
        return state

def run_principal_engineer(state: MessagesState, config: dict) -> MessagesState:
    """Handle Principal Engineer's response."""
    query = state['message']
    
    try:
        agent = CSICAgent.create("PRINCIPAL_ENGINEER", "system", query)
        response = agent.actor()
        return {
            "message": f"Principal Engineer: {response}"
        }
    except Exception as e:
        print(f"Principal Engineer Error: {str(e)}")
        return state

def summarize_discussion(state: MessagesState, config: RunnableConfig):
    """Generate final summary of the panel discussion."""
    discussion_text = state['message']
    
    summary_prompt = """Analyze and summarize the engineering panel discussion.
    Focus on:
    1. Key technical insights
    2. Areas of agreement
    3. Different perspectives offered
    4. Concrete recommendations
    
    Discussion to summarize:
    {discussion}
    """
    
    response = model.invoke([
        SystemMessage(content=summary_prompt.format(discussion=discussion_text)),
        HumanMessage(content=discussion_text)
    ])
    
    return {
        "message": f"Summary: {response.content}"
    }

# Create the graph
builder = StateGraph(MessagesState, config_schema=configuration.Configuration)

# Add nodes
builder.add_node("run_panel", run_panel_discussions)
builder.add_node("project_manager_response", run_project_manager)
builder.add_node("senior_engineer_response", run_senior_engineer)
builder.add_node("principal_engineer_response", run_principal_engineer)
builder.add_node("summarize_panel", summarize_discussion)

# Define the flow
builder.add_edge(START, "run_panel")
# Panel members respond in parallel after query reformulation
builder.add_edge("run_panel", "project_manager_response")
builder.add_edge("run_panel", "senior_engineer_response")
builder.add_edge("run_panel", "principal_engineer_response")
# All responses go to summary
builder.add_edge("project_manager_response", "summarize_panel")
builder.add_edge("senior_engineer_response", "summarize_panel")
builder.add_edge("principal_engineer_response", "summarize_panel")
builder.add_edge("summarize_panel", END)

# Compile the graph
graph = builder.compile() 