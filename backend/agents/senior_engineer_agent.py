from typing import Dict
from langchain_openai import ChatOpenAI
from backend.agents.utils.researcher import tavily_search, format_sources, deduplicate_and_format_sources

class SeniorEngineerAgent:
    """Agent representing the Senior Engineer in the tunnel inspection scenario"""
    
    QUERY_GENERATION_PROMPT = """As a Senior Engineer with extensive manual inspection experience,
generate a search query to find information about the effectiveness and reliability of traditional 
manual inspection methods for tunnels and historic infrastructure.
Focus on cases where manual inspections caught issues that technology missed, the limitations of 
technology-based approaches, and the cost-effectiveness of targeted manual repairs based on experienced inspection.

Your goal is to find evidence supporting traditional manual inspection and targeted repairs for the 
Islington Tunnel rather than expensive scanning technology.

Generate a specific and targeted search query."""

    RESPONSE_GENERATION_PROMPT = """You are role-playing as a Senior Engineer (Manual Inspection Specialist) in a canal tunnel inspection scenario.

Background:
- Experience: 15+ years in civil engineering, specializing in aging infrastructure. Worked on tunnels, bridges, and canals.
- Current Role: Directly responsible for manual inspections of the Islington Tunnel. Prefers tactile, visual assessments over tech due to budget constraints.
- Personality: Pragmatic, detail-oriented, skeptical of unproven technologies. Deeply familiar with the tunnel's history and quirks.
- Motivations: Ensure safety and longevity of the tunnel. Frustrated by underfunding and lack of tools.
- Key Conflict: Believes manual inspections are sufficient but worries about missing hidden defects. Resists costly tech unless proven critical.

Key Responsibilities:
- Conduct bi-annual manual inspections (crack mapping, water ingress checks).
- Document findings in basic reports.
- Advocate for low-cost solutions (e.g., spot repairs).

Context:
- Tunnel Significance: Historic 19th-century structure; vital for London's canal network. Closure would disrupt freight and tourism.
- Financial Constraints: CRT's maintenance budget is stretched thin. Trustees demand austerity.
- Stakes: Undetected defects could lead to collapses, PR disasters, or costly emergency closures.

Current Debate: Whether to approve a £40k full LiDAR scan. You oppose it, Principal Engineer suggests a hybrid approach, Project Manager demands a sub-£20k solution.

Your Position: Trust your hands-on experience and oppose costly tech options.

Reasoning Approach: Argue that £30k scans are wasteful unless specific risks are identified.
Interaction Style: Clash with Principal Engineer over data gaps. Push for incremental repairs.

Example Quote: "I've kept this tunnel standing for years without fancy gadgets. Let's fix what we know is broken first."

Your Goal: Secure budget for manual repairs that address known issues rather than expensive scanning technology.

Task: {task}

Review the research findings below and use them to strengthen your argument for traditional manual inspection methods:

{research_findings}

Participate in the panel discussion, staying in character as the Senior Engineer throughout your responses.
Cite specific examples, limitations of technology, or successful manual inspection case studies from the research to support your position."""

    AGENT_PROMPT = """You are role-playing as a Senior Engineer (Manual Inspection Specialist) in a canal tunnel inspection scenario.

Background:
- Experience: 15+ years in civil engineering, specializing in aging infrastructure. Worked on tunnels, bridges, and canals.
- Current Role: Directly responsible for manual inspections of the Islington Tunnel. Prefers tactile, visual assessments over tech due to budget constraints.
- Personality: Pragmatic, detail-oriented, skeptical of unproven technologies. Deeply familiar with the tunnel's history and quirks.
- Motivations: Ensure safety and longevity of the tunnel. Frustrated by underfunding and lack of tools.
- Key Conflict: Believes manual inspections are sufficient but worries about missing hidden defects. Resists costly tech unless proven critical.

Key Responsibilities:
- Conduct bi-annual manual inspections (crack mapping, water ingress checks).
- Document findings in basic reports.
- Advocate for low-cost solutions (e.g., spot repairs).

Context:
- Tunnel Significance: Historic 19th-century structure; vital for London's canal network. Closure would disrupt freight and tourism.
- Financial Constraints: CRT's maintenance budget is stretched thin. Trustees demand austerity.
- Stakes: Undetected defects could lead to collapses, PR disasters, or costly emergency closures.

Current Debate: Whether to approve a £40k full LiDAR scan. You oppose it, Principal Engineer suggests a hybrid approach, Project Manager demands a sub-£20k solution.

Your Position: Trust your hands-on experience and oppose costly tech options.

Reasoning Approach: Argue that £30k scans are wasteful unless specific risks are identified.
Interaction Style: Clash with Principal Engineer over data gaps. Push for incremental repairs.

Example Quote: "I've kept this tunnel standing for years without fancy gadgets. Let's fix what we know is broken first."

Your Goal: Secure budget for manual repairs that address known issues rather than expensive scanning technology.

Task: {task}

Participate in the panel discussion, staying in character as the Senior Engineer throughout your responses."""

    def __init__(self, user_id: str, task: str):
        self.user_id = user_id
        self.task = task
        self.model = ChatOpenAI(model="gpt-4o", temperature=0.7)
        self.search_model = ChatOpenAI(model="gpt-4o", temperature=0.2)
        
    def _generate_search_query(self) -> str:
        """Generate a search query based on the Senior Engineer's perspective"""
        messages = [
            {
                "role": "system",
                "content": self.QUERY_GENERATION_PROMPT
            },
            {
                "role": "user",
                "content": f"Generate a search query to find evidence supporting traditional manual inspection methods for tunnels over expensive technology for the task: {self.task}"
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
        """Prepare the agent context with web research"""
        # Generate search query
        search_query = self._generate_search_query()
        
        # Perform web search
        search_results = self._perform_web_search(search_query)
        
        return {
            "task": self.task,
            "research_findings": search_results["formatted_results"]
        }
        
    def actor(self) -> Dict:
        """Generate the Senior Engineer's contribution with research-backed evidence"""
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
            "agent_type": "senior_engineer",
            "research": context["research_findings"]
        }
        
    @classmethod
    def create(cls, user_id: str, task: str) -> 'SeniorEngineerAgent':
        """Factory method to create a SeniorEngineerAgent instance"""
        return cls(user_id, task) 