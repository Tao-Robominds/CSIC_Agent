from dataclasses import dataclass
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI

@dataclass
class EvaluationCriteria:
    """Criteria for evaluating panel discussion summaries"""
    completeness: bool  # Does it address all aspects of the original task?
    actionability: bool  # Are the action items specific and implementable?
    clarity: bool  # Is the summary clear and well-structured?
    stakeholder_alignment: bool  # Do the conclusions align with all stakeholders' inputs?
    feasibility: bool  # Are the proposed solutions feasible given constraints?

class EvaluatorAgent:
    """Agent responsible for evaluating panel discussion summaries"""
    
    EVALUATION_PROMPT = """You are a critical evaluator of panel discussions focused on infrastructure decision-making. Your task is to evaluate the summary of a discussion about tunnel inspection strategies for the Islington Tunnel.

Background Context:
This is a historic 19th-century canal tunnel with budget constraints. The discussion involved three stakeholders:
1. Senior Engineer (Manual Inspection Specialist): Advocates for traditional manual inspections and targeted repairs
2. Principal Engineer (Asset Management Lead): Supports a hybrid approach using targeted technology in high-risk areas 
3. Project Manager (Oversight): Focused on keeping costs under £20k while managing risks

Evaluate the panel discussion summary based on the following criteria:

1. Completeness: Does the summary address all aspects of the original task/question? Does it capture all key perspectives?
2. Actionability: Are the action items specific, measurable, implementable, and cost-aware?
3. Clarity: Is the summary clear, well-structured, and easy to understand?
4. Stakeholder Alignment: Do the conclusions reflect and balance the concerns of all three stakeholders?
5. Feasibility: Are the proposed solutions feasible given the £20k budget constraint and technical requirements?

For each criterion, provide:
- A boolean assessment (True/False)
- A brief explanation of your assessment (2-3 sentences)
- If False, specific suggestions for improvement

Original Task: {task}

Panel Summary:
{summary}

Evaluate strictly and provide specific, actionable feedback."""

    def __init__(self, user_id: str, task: str, summary: str):
        self.user_id = user_id
        self.task = task
        self.summary = summary
        self.model = ChatOpenAI(model="gpt-4o", temperature=0)

    def perceiver(self) -> Dict[str, str]:
        """Prepare the evaluation context"""
        return {
            "task": self.task,
            "summary": self.summary
        }

    def actor(self) -> Dict:
        """Evaluate the panel discussion summary"""
        context = self.perceiver()
        
        messages = [
            {
                "role": "system",
                "content": self.EVALUATION_PROMPT.format(**context)
            }
        ]

        # Call GPT for evaluation
        response = self.model.invoke(messages)
        
        # Parse the evaluation results
        evaluation = self._parse_evaluation(response.content)
        
        # Calculate if the summary passes all criteria
        passes_evaluation = all([
            evaluation.completeness,
            evaluation.actionability,
            evaluation.clarity,
            evaluation.stakeholder_alignment,
            evaluation.feasibility
        ])

        # Ensure our evaluation is consistent
        if not passes_evaluation and "passes all criteria" in response.content.lower():
            print("Warning: Inconsistency detected. Evaluator claims summary passes but individual criteria failed.")
        
        # Override the evaluator's pass/fail decision with our calculated one
        return {
            "passes": passes_evaluation,
            "criteria": evaluation,
            "suggestions": self._get_improvement_suggestions(response.content),
            "full_evaluation": response.content
        }

    def _parse_evaluation(self, response: str) -> EvaluationCriteria:
        """Parse the GPT response into structured evaluation criteria"""
        # Enhanced parsing that looks for explicit pass/fail statements
        completeness_patterns = ["completeness: false", "completeness:false", "not complete", "lacks completeness", "completeness is false"]
        actionability_patterns = ["actionability: false", "actionability:false", "not actionable", "lacks actionability", "actionability is false"]
        clarity_patterns = ["clarity: false", "clarity:false", "not clear", "lacks clarity", "clarity is false"]
        alignment_patterns = ["stakeholder alignment: false", "stakeholder alignment:false", "not aligned", "lacks alignment", "alignment is false", "stakeholder_alignment: false"]
        feasibility_patterns = ["feasibility: false", "feasibility:false", "not feasible", "lacks feasibility", "feasibility is false"]
        
        response_lower = response.lower()
        
        # Check for matches to failure patterns
        completeness = not any(pattern in response_lower for pattern in completeness_patterns)
        actionability = not any(pattern in response_lower for pattern in actionability_patterns)
        clarity = not any(pattern in response_lower for pattern in clarity_patterns)
        stakeholder_alignment = not any(pattern in response_lower for pattern in alignment_patterns)
        feasibility = not any(pattern in response_lower for pattern in feasibility_patterns)
        
        # Double-check by looking for explicit "False" after criterion name
        if "**completeness:" in response_lower and "false" in response_lower.split("**completeness:", 1)[1].split("\n", 1)[0].lower():
            completeness = False
        if "**actionability:" in response_lower and "false" in response_lower.split("**actionability:", 1)[1].split("\n", 1)[0].lower():
            actionability = False
        if "**clarity:" in response_lower and "false" in response_lower.split("**clarity:", 1)[1].split("\n", 1)[0].lower():
            clarity = False
        if "**stakeholder alignment:" in response_lower and "false" in response_lower.split("**stakeholder alignment:", 1)[1].split("\n", 1)[0].lower():
            stakeholder_alignment = False
        if "**feasibility:" in response_lower and "false" in response_lower.split("**feasibility:", 1)[1].split("\n", 1)[0].lower():
            feasibility = False
        
        return EvaluationCriteria(
            completeness=completeness,
            actionability=actionability,
            clarity=clarity,
            stakeholder_alignment=stakeholder_alignment,
            feasibility=feasibility
        )

    def _get_improvement_suggestions(self, response: str) -> List[str]:
        """Extract improvement suggestions from the evaluation response"""
        suggestions = []
        lines = response.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ["suggest", "improve", "recommendation", "should", "could", "needs to"]):
                suggestions.append(line.strip())
        return suggestions

    @classmethod
    def create(cls, user_id: str, task: str, summary: str) -> 'EvaluatorAgent':
        """Factory method to create an EvaluatorAgent instance"""
        return cls(user_id, task, summary) 