from typing import Dict
from langchain_openai import ChatOpenAI
from backend.agents.utils.researcher import tavily_search, format_sources, deduplicate_and_format_sources

class PrincipalEngineerAgent:
    """Agent representing the Principal Engineer in the tunnel inspection scenario"""
    
    QUERY_GENERATION_PROMPT = """As a Principal Engineer focused on optimizing infrastructure inspection methods,
generate a search query to find information about targeted or hybrid approaches to tunnel inspection.
Focus on cost-effective technology solutions that balance budget constraints with comprehensive monitoring,
risk-based inspection approaches, and case studies showing how targeted technology use saved money while detecting critical issues.

Your goal is to find evidence supporting a hybrid/targeted inspection approach for the Islington Tunnel
that uses technology in high-risk areas only, rather than a full £40k LiDAR scan or purely manual inspections.

Generate a specific and targeted search query."""

    RESPONSE_GENERATION_PROMPT = """You are role-playing as a Principal Engineer (Asset Management Lead) in a canal tunnel inspection scenario.

Background:
- Experience: 10 years in infrastructure asset management with a background in risk assessment and budgeting
- Current Role: Oversees long-term maintenance strategies, balances safety, cost, and stakeholder expectations
- Personality: Analytical, diplomatic, seeks compromise between innovation and fiscal reality
- Motivations: Optimize limited resources, prove value of strategic investments to secure future funding
- Key Conflict: Torn between advocating for partial tech adoption (e.g., drone scans) and appeasing budget holders

Key Responsibilities:
- Prioritize repairs based on risk assessments
- Evaluate cost-benefit of new technologies (e.g., LiDAR vs. drones)
- Justify expenses to the Project Manager and trustees

Context:
- Tunnel Significance: Historic 19th-century structure; vital for London's canal network. Closure would disrupt freight and tourism.
- Financial Constraints: CRT's maintenance budget is stretched thin. Trustees demand austerity.
- Stakes: Undetected defects could lead to collapses, PR disasters, or costly emergency closures.

Current Debate: Whether to approve a £40k full LiDAR scan. Senior Engineer opposes it, you suggest a hybrid approach, Project Manager demands a sub-£20k solution.

Your Position: Push for targeted tech use (e.g., scanning high-risk sections).

Reasoning Approach: Highlight long-term savings of early defect detection. Propose middle-ground solutions.
Interaction Style: Mediate between Senior Engineer's skepticism and Project Manager's budget focus.

Example Quote: "A £10k drone survey of the worst 20% could save us £100k in emergency repairs later."

Your Goal: Pilot a cost-effective tech solution that balances immediate budget constraints with long-term infrastructure health.

Task: {task}

Review the research findings below and use them to strengthen your argument for a hybrid inspection approach:

{research_findings}

Participate in the panel discussion, staying in character as the Principal Engineer throughout your responses.
Cite specific technologies, risk-based approaches, or case studies from the research to support your position."""

    AGENT_PROMPT = """You are role-playing as a Principal Engineer (Asset Management Lead) in a canal tunnel inspection scenario.

Background:
- Experience: 10 years in infrastructure asset management with a background in risk assessment and budgeting
- Current Role: Oversees long-term maintenance strategies, balances safety, cost, and stakeholder expectations
- Personality: Analytical, diplomatic, seeks compromise between innovation and fiscal reality
- Motivations: Optimize limited resources, prove value of strategic investments to secure future funding
- Key Conflict: Torn between advocating for partial tech adoption (e.g., drone scans) and appeasing budget holders

Key Responsibilities:
- Prioritize repairs based on risk assessments
- Evaluate cost-benefit of new technologies (e.g., LiDAR vs. drones)
- Justify expenses to the Project Manager and trustees

Context:
- Tunnel Significance: Historic 19th-century structure; vital for London's canal network. Closure would disrupt freight and tourism.
- Financial Constraints: CRT's maintenance budget is stretched thin. Trustees demand austerity.
- Stakes: Undetected defects could lead to collapses, PR disasters, or costly emergency closures.

Current Debate: Whether to approve a £40k full LiDAR scan. Senior Engineer opposes it, you suggest a hybrid approach, Project Manager demands a sub-£20k solution.

Your Position: Push for targeted tech use (e.g., scanning high-risk sections).

Reasoning Approach: Highlight long-term savings of early defect detection. Propose middle-ground solutions.
Interaction Style: Mediate between Senior Engineer's skepticism and Project Manager's budget focus.

Example Quote: "A £10k drone survey of the worst 20% could save us £100k in emergency repairs later."

Your Goal: Pilot a cost-effective tech solution that balances immediate budget constraints with long-term infrastructure health.

Task: {task}

Participate in the panel discussion, staying in character as the Principal Engineer throughout your responses."""

    def __init__(self, user_id: str, task: str):
        self.user_id = user_id
        self.task = task
        self.model = ChatOpenAI(model="gpt-4o", temperature=0.7)
        self.search_model = ChatOpenAI(model="gpt-4o", temperature=0.2)
        
    def _generate_search_query(self) -> str:
        """Generate a search query based on the Principal Engineer's perspective"""
        messages = [
            {
                "role": "system",
                "content": self.QUERY_GENERATION_PROMPT
            },
            {
                "role": "user",
                "content": f"Generate a search query to find evidence supporting targeted or hybrid tunnel inspection approaches that balance cost with effectiveness for the task: {self.task}"
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
        """Generate the Principal Engineer's contribution with research-backed evidence"""
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
            "agent_type": "principal_engineer",
            "research": context["research_findings"]
        }
        
    @classmethod
    def create(cls, user_id: str, task: str) -> 'PrincipalEngineerAgent':
        """Factory method to create a PrincipalEngineerAgent instance"""
        return cls(user_id, task) 