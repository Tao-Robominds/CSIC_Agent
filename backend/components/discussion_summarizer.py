from backend.components.gpt_parser import GPTComponent, GPTRequest

class DiscussionSummarizer:
    SECTION_HEADERS = [
        'Panel Discussion Summary:',
        'Discussion Overview:',
        'Communication Flow:',
        'Key Participants:',
        'Main Conclusions:',
        'Action Plans:'
    ]

    SYSTEM_PROMPT = """You are a strategic business consultant. Synthesize the team discussion into a clear report.
Your response must follow this exact structure and formatting:

1. Start with 'Panel Discussion Summary:' as a standalone line

2. Under 'Discussion Overview:', provide 2-3 sentences about the context and main focus

3. Under 'Communication Flow:', describe in bullet points how the discussion progressed:
   - First, [what happened]
   - Then, [next step]
   - Finally, [conclusion]

4. Under 'Key Participants:', list each executive's contribution:
   - CEO: [main points]
   - CFO: [main points]
   - CMO: [main points]

5. Under 'Main Conclusions:', list 2-3 key takeaways in bullet points

6. End with 'Action Plans:' followed by 3-5 numbered, specific action items

Keep each section concise and clearly separated with blank lines.
Use bullet points and numbers as specified above."""

    def __init__(self, task_prompt: str, conversation_history: list):
        self.task_prompt = task_prompt
        self.conversation_history = conversation_history

    def _format_discussion_with_dependencies(self) -> str:
        """Format the discussion history with dependencies and timing."""
        formatted_messages = []
        
        for msg in self.conversation_history:
            message_parts = []
            message_parts.append(f"## {msg.get('role', 'Unknown')}'s Input:")
            message_parts.append(msg.get('content', ''))
            
            if deps := msg.get('dependencies'):
                message_parts.append(f"Built upon input from: {', '.join(deps)}")
            if time := msg.get('response_time'):
                message_parts.append(f"Response time: {time}")
            
            formatted_messages.append('\n'.join(message_parts))
            
        return "\n\n".join(formatted_messages)

    def generate_summary(self) -> str:
        """Generate a formatted summary of the panel discussion."""
        messages = [
            {
                "role": "system",
                "content": self.SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": (
                    f"Original task: {self.task_prompt}\n\n"
                    f"Team discussion and dependencies:\n"
                    f"{self._format_discussion_with_dependencies()}\n\n"
                    "Please synthesize this discussion following the exact format specified."
                )
            }
        ]

        response = GPTComponent(
            GPTRequest(
                messages=messages,
                model="gpt-4o",
                temperature=0.1,
                max_tokens=1000
            )
        ).actor()
        
        return self._format_summary(response["response"])

    def _format_summary(self, raw_summary: str | list) -> str:
        """Post-process the summary to ensure consistent formatting."""
        if isinstance(raw_summary, list):
            raw_summary = '\n'.join(raw_summary)
        
        formatted_sections = []
        for line in raw_summary.split('\n'):
            line = line.replace('#', '').replace('*', '').strip()
            if not line:
                continue
            
            if any(header in line for header in self.SECTION_HEADERS):
                formatted_sections.extend(['', line, ''])
            elif line.startswith('- '):
                formatted_sections.append('  ' + line)
            elif line[0].isdigit() and '. ' in line[:4]:
                formatted_sections.append('  ' + line)
            else:
                formatted_sections.append(line)
        
        return '\n'.join(formatted_sections) 