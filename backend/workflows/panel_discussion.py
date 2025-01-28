#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from dotenv import load_dotenv
import json

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
    summary: str

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

    def get_executive_response(self, state: PanelState) -> PanelState:
        """Get responses from selected executives."""
        inquiry = state["inquiry"]
        responses = {}
        
        agent_map = {
            "CEO": self.ceo,
            "CFO": self.cfo,
            "CMO": self.cmo
        }
        
        for agent_name in state["selected_agents"]:
            if agent_name in agent_map:
                agent = agent_map[agent_name]
                agent.request = inquiry
                responses[agent_name] = agent.actor()
                
        return {"responses": responses}

    def summarize_discussion(self, state: PanelState) -> PanelState:
        """Summarize the panel discussion."""
        inquiry = state["inquiry"]
        responses = state["responses"]
        
        conversation_history = [
            {"role": role, "content": content}
            for role, content in responses.items()
        ]
        
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
        """Create the workflow graph."""
        workflow = StateGraph(PanelState)

        # Add nodes
        workflow.add_node("select_panel", self.select_panel_members)
        workflow.add_node("get_responses", self.get_executive_response)
        workflow.add_node("summarize", self.summarize_discussion)

        # Add edges
        workflow.add_edge(START, "select_panel")
        workflow.add_edge("select_panel", "get_responses")

        # Add conditional edge after getting responses
        workflow.add_conditional_edges(
            "get_responses",
            self.should_end,
            {
                "summarize": "summarize",
                "get_responses": "get_responses"
            }
        )
        workflow.add_edge("summarize", END)

        return workflow

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