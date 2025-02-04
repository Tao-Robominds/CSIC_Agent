#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from dotenv import load_dotenv
import json
from datetime import datetime

from typing import Annotated, List, TypedDict
from typing_extensions import TypedDict
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import add_messages

from backend.agents.panel_admin import PanelAdminAgent
from backend.agents.ceo import CEOAgent
from backend.agents.cmo import CMOAgent
from backend.agents.cfo import CFOAgent
from backend.components.discussion_summarizer import DiscussionSummarizer

load_dotenv()

class PanelState(TypedDict):
    """State for panel discussion."""
    messages: Annotated[List[HumanMessage | AIMessage], add_messages]
    inquiry: str
    selected_agents: List[str]
    responses: dict
    dependencies: dict  # Track which agent needs input from other agents
    communication_chain: List[dict]  # Track the flow of messages between agents
    summary: str

class AgentMessage:
    """Structure for messages between agents"""
    def __init__(self, from_agent: str, to_agent: str, content: str, depends_on: List[str] = None):
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.content = content
        self.depends_on = depends_on or []
        self.timestamp = datetime.now()

class PanelDiscussionWorkflow:
    def __init__(self):
        # Initialize agents
        self.panel_admin = PanelAdminAgent(user_id="system", request=None)
        self.ceo = CEOAgent(user_id="system", request=None)
        self.cfo = CFOAgent(user_id="system", request=None)
        self.cmo = CMOAgent(user_id="system", request=None)
        
        # Create and compile the workflow
        self.workflow = self._create_workflow()
        self.panel_discussion = self.workflow.compile()

    def select_panel_members(self, state: PanelState) -> PanelState:
        """Panel admin selects which C-level executives should participate."""
        inquiry = state["inquiry"]
        self.panel_admin.request = inquiry
        admin_response = self.panel_admin.actor()
        
        try:
            admin_response = admin_response.replace(';', ',')
            participants_data = json.loads(admin_response)
            selected = participants_data.get('invited', [])
            
            if 'inquiry' in participants_data:
                state["inquiry"] = participants_data['inquiry']
                
            return {"selected_agents": selected}
        except json.JSONDecodeError:
            return {"selected_agents": ["CEO", "CMO", "CFO"]}

    def ceo_node(self, state: PanelState) -> PanelState:
        """CEO's response and dependency identification."""
        self.ceo.request = state["inquiry"]
        response = self.ceo.actor()
        
        # Check if CEO needs input from other executives
        dependencies = self._analyze_dependencies(response, "CEO")
        
        return {
            "responses": {**state.get("responses", {}), "CEO": response},
            "dependencies": {**state.get("dependencies", {}), "CEO": dependencies},
            "communication_chain": [*state.get("communication_chain", []), {
                "agent": "CEO",
                "response": response,
                "dependencies": dependencies
            }]
        }

    def cfo_node(self, state: PanelState) -> PanelState:
        """CFO's response with consideration of CEO's input if needed."""
        # Check if CFO needs to wait for CEO input
        ceo_response = state.get("responses", {}).get("CEO")
        
        self.cfo.request = self._prepare_request(
            state["inquiry"], 
            state.get("communication_chain", [])
        )
        response = self.cfo.actor()
        dependencies = self._analyze_dependencies(response, "CFO")
        
        return {
            "responses": {**state.get("responses", {}), "CFO": response},
            "dependencies": {**state.get("dependencies", {}), "CFO": dependencies},
            "communication_chain": [*state.get("communication_chain", []), {
                "agent": "CFO",
                "response": response,
                "dependencies": dependencies
            }]
        }

    def cmo_node(self, state: PanelState) -> PanelState:
        """CMO's response with consideration of previous inputs."""
        self.cmo.request = self._prepare_request(
            state["inquiry"], 
            state.get("communication_chain", [])
        )
        response = self.cmo.actor()
        dependencies = self._analyze_dependencies(response, "CMO")
        
        return {
            "responses": {**state.get("responses", {}), "CMO": response},
            "dependencies": {**state.get("dependencies", {}), "CMO": dependencies},
            "communication_chain": [*state.get("communication_chain", []), {
                "agent": "CMO",
                "response": response,
                "dependencies": dependencies
            }]
        }

    def _analyze_dependencies(self, response: str, agent: str) -> List[str]:
        """Analyze response to identify dependencies on other executives."""
        # Use GPT to analyze the response and identify dependencies
        analysis_prompt = f"""
        Analyze this response from the {agent} and identify which other executives' input might be needed:
        {response}
        
        Return only the list of required executives (CEO, CFO, CMO) or empty list if none required.
        """
        # Implementation of dependency analysis...
        return []

    def _prepare_request(self, inquiry: str, communication_chain: List[dict]) -> str:
        """Prepare request with context from previous responses."""
        context = "\n\n".join([
            f"{msg['agent']}: {msg['response']}"
            for msg in communication_chain
        ])
        
        return f"""Original inquiry: {inquiry}

Previous responses:
{context}

Please consider the above context in your response."""

    def summarize_discussion(self, state: PanelState) -> PanelState:
        """Summarize the panel discussion."""
        inquiry = state["inquiry"]
        
        # Create conversation history with dependencies
        conversation_history = []
        for msg in state.get("communication_chain", []):
            conversation_history.append({
                "role": msg["agent"],
                "content": msg["response"],
                "dependencies": msg["dependencies"]
            })
        
        summarizer = DiscussionSummarizer(inquiry, conversation_history)
        summary = summarizer.generate_summary()
        
        return {"summary": summary}

    @staticmethod
    def should_end(state: PanelState) -> str:
        """Determine if we should end after getting responses."""
        if state.get("responses"):
            return "summarize"
        return "get_responses"

    def _create_workflow(self) -> StateGraph:
        """Create the workflow graph with communication between agents."""
        workflow = StateGraph(PanelState)

        # Add nodes
        workflow.add_node("select_panel", self.select_panel_members)
        workflow.add_node("ceo_response", self.ceo_node)
        workflow.add_node("cfo_response", self.cfo_node)
        workflow.add_node("cmo_response", self.cmo_node)
        workflow.add_node("summarize", self.summarize_discussion)

        # Add edges
        workflow.add_edge(START, "select_panel")
        workflow.add_edge("select_panel", "ceo_response")
        
        # Add conditional edges based on dependencies
        workflow.add_conditional_edges(
            "ceo_response",
            self._route_after_ceo,
            {
                "cfo_response": "cfo_response",
                "cmo_response": "cmo_response",
                "summarize": "summarize"
            }
        )
        
        workflow.add_conditional_edges(
            "cfo_response",
            self._route_after_cfo,
            {
                "cmo_response": "cmo_response",
                "summarize": "summarize"
            }
        )
        
        workflow.add_edge("cmo_response", "summarize")
        workflow.add_edge("summarize", END)

        return workflow

    def _route_after_ceo(self, state: PanelState) -> str:
        """Route to next node based on CEO's response dependencies."""
        deps = state.get("dependencies", {}).get("CEO", [])
        if "CFO" in deps:
            return "cfo_response"
        elif "CMO" in deps:
            return "cmo_response"
        return "summarize"

    def _route_after_cfo(self, state: PanelState) -> str:
        """Route to next node based on CFO's response dependencies."""
        deps = state.get("dependencies", {}).get("CFO", [])
        if "CMO" in deps:
            return "cmo_response"
        return "summarize"

    def run(self, inquiry: str) -> str:
        """Run the panel discussion workflow."""
        result = self.panel_discussion.invoke({
            "inquiry": inquiry,
            "messages": [],
            "selected_agents": [],
            "responses": {},
            "summary": ""
        })
        return result["summary"]

workflow = PanelDiscussionWorkflow()
panel_discussion = workflow.workflow