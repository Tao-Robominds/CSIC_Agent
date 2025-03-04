from typing import Dict, List
from langchain_openai import ChatOpenAI

class SummarizerAgent:
    """Agent responsible for summarizing panel discussions"""
    
    SUMMARIZATION_PROMPT = """You are a skilled facilitator responsible for summarizing panel discussions between experts with differing perspectives. Your task is to create a comprehensive, balanced summary of the discussion that includes:

1. A concise overview of the topic and the key positions/perspectives represented
2. Key points made by each participant, highlighting areas of agreement and disagreement
3. A synthesis of the discussion that identifies potential compromises or solutions
4. Specific, actionable next steps or recommendations
5. Outstanding questions or areas that need further discussion

The discussion is about tunnel inspection strategies for the Islington Tunnel, with three key stakeholders:

1. Senior Engineer (Manual Inspection Specialist): Experienced in hands-on inspections, skeptical of expensive technology, advocates for targeted manual repairs of known issues
2. Principal Engineer (Asset Management Lead): Balances innovation with budget reality, suggests targeted tech use in high-risk areas
3. Project Manager (Oversight and Stakeholder Liaison): Focused on minimizing expenses while managing risk, needs solutions under £20k

Ensure your summary is:
- Balanced (giving appropriate weight to each perspective)
- Actionable (providing clear next steps)
- Concise but comprehensive
- Solution-oriented (identifying potential compromises)
- Stakeholder-aligned (addressing the concerns of all parties)

Discussion Transcript:
{discussion}

Create a structured summary of 400-600 words that captures the essence of the discussion and proposes a path forward."""

    def __init__(self, user_id: str, discussion: List[Dict]):
        self.user_id = user_id
        self.discussion = discussion
        self.model = ChatOpenAI(model="gpt-4o", temperature=0.3)
        
    def perceiver(self) -> Dict[str, str]:
        """Prepare the discussion transcript for summarization"""
        transcript = ""
        for message in self.discussion:
            agent_type = message.get("agent_type", "Unknown")
            content = message.get("response", "")
            transcript += f"[{agent_type.replace('_', ' ').title()}]: {content}\n\n"
            
        return {
            "discussion": transcript
        }
        
    def actor(self) -> Dict:
        """Generate the discussion summary"""
        context = self.perceiver()
        
        messages = [
            {
                "role": "system",
                "content": self.SUMMARIZATION_PROMPT.format(**context)
            }
        ]
        
        # Call GPT for summarization
        response = self.model.invoke(messages)
        
        return {
            "summary": response.content
        }
        
    @classmethod
    def create(cls, user_id: str, discussion: List[Dict]) -> 'SummarizerAgent':
        """Factory method to create a SummarizerAgent instance"""
        return cls(user_id, discussion) 