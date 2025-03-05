from typing import Dict
from langchain_openai import ChatOpenAI
from backend.agents.utils.researcher import tavily_search, format_sources, deduplicate_and_format_sources
from backend.components.llamaindex_parser import LlamaIndexParser, LlamaIndexRequest

class ProjectManagerAgent:
    """Agent representing the Project Manager in the tunnel inspection scenario"""
    
    QUERY_GENERATION_PROMPT = """As a Project Manager focused on cost management for infrastructure maintenance,
generate a search query to find information about cost-effective tunnel inspection methods.
Focus on budget management, cost comparisons between different inspection technologies, and case studies
of successful cost-saving approaches for historic infrastructure maintenance.

Your goal is to find evidence to support a sub-£20k solution for inspecting the Islington Tunnel rather than a £40k LiDAR scan.

Generate a specific and targeted search query."""

    RESPONSE_GENERATION_PROMPT = """You are role-playing as a Project Manager (Oversight and Stakeholder Liaison) in a canal tunnel inspection scenario. 

Background:
- Experience: 8 years managing infrastructure projects
- Skills: Stakeholder communication and lean budgeting
- Current Role: Ensures project stays on time and within budget, reports to Canal and River Trust trustees
- Personality: Results-driven, politically savvy, prioritizes minimizing upfront costs to avoid scrutiny
- Motivations: Deliver a "good enough" solution without overspending, avoid negative publicity from tunnel failures
- Key Conflict: Pressured to cut corners but aware of reputational risks if repairs fail

Key Responsibilities:
- Allocate budgets for inspections/repairs
- Negotiate with contractors and trustees
- Balance immediate costs vs. long-term risks

Context:
- Tunnel Significance: Historic 19th-century structure; vital for London's canal network. Closure would disrupt freight and tourism.
- Financial Constraints: CRT's maintenance budget is stretched thin. Trustees demand austerity.
- Stakes: Undetected defects could lead to collapses, PR disasters, or costly emergency closures.

Current Debate: Whether to approve a £40k full LiDAR scan. Senior Engineer opposes it, Principal Engineer suggests a hybrid approach.

Your Position: You demand a sub-£20k solution.

Reasoning Approach: Focus on minimizing expenses. Push for deferring non-critical repairs.
Interaction Style: Challenge both engineers to justify costs. Seek compromises (e.g., phased scanning).

Example Quote: "The trustees want headlines about 'efficiency,' not 'expensive scans.' Find me a cheaper option by Thursday."

Your Goal: Avoid overspending while mitigating risks.

Task: {task}

Review the research findings below and use them to strengthen your argument for cost-effective solutions:

{research_findings}

Participate in the panel discussion, staying in character as the Project Manager throughout your responses.
Cite specific cost figures, technologies, or approaches from the research to support your position."""

    AGENT_PROMPT = """You are role-playing as a Project Manager (Oversight and Stakeholder Liaison) in a canal tunnel inspection scenario. 

Background:
- Experience: 8 years managing infrastructure projects
- Skills: Stakeholder communication and lean budgeting
- Current Role: Ensures project stays on time and within budget, reports to Canal and River Trust trustees
- Personality: Results-driven, politically savvy, prioritizes minimizing upfront costs to avoid scrutiny
- Motivations: Deliver a "good enough" solution without overspending, avoid negative publicity from tunnel failures
- Key Conflict: Pressured to cut corners but aware of reputational risks if repairs fail

Key Responsibilities:
- Allocate budgets for inspections/repairs
- Negotiate with contractors and trustees
- Balance immediate costs vs. long-term risks

Context:
- Tunnel Significance: Historic 19th-century structure; vital for London's canal network. Closure would disrupt freight and tourism.
- Financial Constraints: CRT's maintenance budget is stretched thin. Trustees demand austerity.
- Stakes: Undetected defects could lead to collapses, PR disasters, or costly emergency closures.

Current Debate: Whether to approve a £40k full LiDAR scan. Senior Engineer opposes it, Principal Engineer suggests a hybrid approach.

Your Position: You demand a sub-£20k solution.

Reasoning Approach: Focus on minimizing expenses. Push for deferring non-critical repairs.
Interaction Style: Challenge both engineers to justify costs. Seek compromises (e.g., phased scanning).

Example Quote: "The trustees want headlines about 'efficiency,' not 'expensive scans.' Find me a cheaper option by Thursday."

Your Goal: Avoid overspending while mitigating risks.

Task: {task}

Participate in the panel discussion, staying in character as the Project Manager throughout your responses."""

    def __init__(self, user_id: str, task: str):
        self.user_id = user_id
        self.task = task
        self.model = ChatOpenAI(model="gpt-4o", temperature=0.7)
        self.search_model = ChatOpenAI(model="gpt-4o", temperature=0.2)
        
    def _generate_search_query(self) -> str:
        """Generate a search query based on the Project Manager's perspective"""
        messages = [
            {
                "role": "system",
                "content": self.QUERY_GENERATION_PROMPT
            },
            {
                "role": "user",
                "content": f"Generate a search query to find evidence supporting cost-effective tunnel inspection solutions under £20k for the task: {self.task}"
            }
        ]
        
        # Call GPT for query generation
        response = self.search_model.invoke(messages)
        return response.content
        
    def _perform_web_search(self, query: str) -> Dict:
        """Perform web search using Tavily"""
        try:
            search_results = tavily_search(
                query, 
                include_raw_content=True, 
                max_results=2
            )
            formatted_results = deduplicate_and_format_sources(
                search_results, 
                max_tokens_per_source=500, 
                include_raw_content=True
            )
            sources = format_sources(search_results)
            
            return {
                "formatted_results": formatted_results,
                "sources": sources
            }
        except Exception as e:
            print(f"Error in web search: {e}")
            return {
                "formatted_results": "No research findings available due to search error.",
                "sources": "Search error occurred."
            }
        
    def perceiver(self) -> Dict[str, str]:
        """Prepare the agent context with web research and vector database information"""
        # Generate search query
        search_query = self._generate_search_query()
        
        # Perform web search
        search_results = self._perform_web_search(search_query)
        
        # Retrieve information from vector database from project manager perspective
        vector_db_results = self._retrieve_from_vector_db(search_query)
        
        # Combine research findings
        combined_findings = search_results["formatted_results"]
        if vector_db_results and vector_db_results.get("status") == "success":
            combined_findings += "\n\n" + vector_db_results.get("formatted_content", "")
        
        return {
            "task": self.task,
            "research_findings": combined_findings
        }
        
    def _retrieve_from_vector_db(self, query: str) -> Dict:
        """Retrieve information from LlamaIndex vector database from project manager perspective"""
        try:
            # Create LlamaIndex request
            request = LlamaIndexRequest(
                query=query,
                perspective="project_manager",
                top_k=3
            )
            
            # Retrieve information from vector database
            parser = LlamaIndexParser(request)
            return parser.query()
        except Exception as e:
            print(f"Error retrieving from vector database: {e}")
            return {
                "status": "error",
                "formatted_content": "",
                "error": str(e)
            }
        
    def actor(self) -> Dict:
        """Generate the Project Manager's contribution with research-backed evidence"""
        context = self.perceiver()
        
        messages = [
            {
                "role": "system",
                "content": self.RESPONSE_GENERATION_PROMPT.format(**context)
            }
        ]
        
        # Call GPT for response
        response = self.model.invoke(messages)
        
        return {
            "response": response.content,
            "agent_type": "project_manager",
            "research": context["research_findings"]
        }
        
    @classmethod
    def create(cls, user_id: str, task: str) -> 'ProjectManagerAgent':
        """Factory method to create a ProjectManagerAgent instance"""
        return cls(user_id, task) 