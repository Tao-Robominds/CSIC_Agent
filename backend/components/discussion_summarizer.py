from backend.components.gpt_parser import GPTComponent, GPTRequest

class DiscussionSummarizer:
    def __init__(self, task_prompt: str, conversation_history: list):
        self.task_prompt = task_prompt
        self.conversation_history = conversation_history

    def generate_summary(self) -> str:
        summary_messages = [
            {"role": "system", "content": (
                "You are a strategic business consultant. Your task is to synthesize "
                "the team discussion into a structured format with clear sections. "
                "Always follow this exact format:\n\n"
                "### Discussion Overview\n"
                "Brief context of the task and key points discussed\n\n"
                "### Key Participants\n"
                "List of executives involved and their main contributions\n\n"
                "### Main Conclusions\n"
                "Core agreements and decisions reached\n\n"
                "### Next Steps\n"
                "List 2-3 immediate actions required in the next week"
            )},
            {"role": "user", "content": (
                f"Original task: {self.task_prompt}\n\n"
                "Team discussion:\n" + 
                "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.conversation_history]) +
                "\n\nPlease synthesize this discussion following the exact format specified."
            )}
        ]

        gpt_request = GPTRequest(
            messages=summary_messages,
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=1000
        )
        
        gpt_component = GPTComponent(gpt_request)
        summary_response = gpt_component.actor()
        
        return summary_response["response"] 