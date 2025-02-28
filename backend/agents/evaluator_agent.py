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
    
    EVALUATION_PROMPT = """You are a critical evaluator of panel discussions. Your task is to evaluate the panel discussion summary based on the following criteria:

1. Completeness: Does the summary address all aspects of the original task/question?
2. Actionability: Are the action items specific, measurable, and implementable?
3. Clarity: Is the summary clear, well-structured, and easy to understand?
4. Stakeholder Alignment: Do the conclusions reflect and align with all stakeholders' inputs?
5. Feasibility: Are the proposed solutions feasible given any mentioned constraints?

For each criterion, provide:
- A boolean assessment (True/False)
- A brief explanation of your assessment
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

        return {
            "passes": passes_evaluation,
            "criteria": evaluation,
            "suggestions": self._get_improvement_suggestions(response.content)
        }

    def _parse_evaluation(self, response: str) -> EvaluationCriteria:
        """Parse the GPT response into structured evaluation criteria"""
        # Simple parsing based on keywords
        return EvaluationCriteria(
            completeness="not complete" not in response.lower(),
            actionability="not actionable" not in response.lower(),
            clarity="not clear" not in response.lower(),
            stakeholder_alignment="not aligned" not in response.lower(),
            feasibility="not feasible" not in response.lower()
        )

    def _get_improvement_suggestions(self, response: str) -> List[str]:
        """Extract improvement suggestions from the evaluation response"""
        suggestions = []
        lines = response.split('\n')
        for line in lines:
            if "suggest" in line.lower() or "improve" in line.lower():
                suggestions.append(line.strip())
        return suggestions

    @classmethod
    def create(cls, user_id: str, task: str, summary: str) -> 'EvaluatorAgent':
        """Factory method to create an EvaluatorAgent instance"""
        return cls(user_id, task, summary) 