from datetime import datetime
from typing import List, Dict, Any
from langchain_core.messages import AIMessage, HumanMessage

from backend.workflows.panel_discussion import PanelDiscussionWorkflow
from langgraph.store.base import BaseStore

class TodoPanelCoordinator:
    """Coordinates between todo list and panel discussions."""
    
    def __init__(self, store: BaseStore, user_id: str):
        self.store = store
        self.user_id = user_id
        self.panel_workflow = PanelDiscussionWorkflow()

    def _extract_participants_from_todo(self, todo: Dict[str, Any]) -> List[str]:
        """Extract relevant participants from todo solutions."""
        participants = set()
        solutions = todo.get('solutions', [])
        
        # Common executive titles to look for
        executives = {'CEO', 'CMO', 'CFO'}
        
        # Look for executives in solutions
        for solution in solutions:
            words = solution.upper().split()
            participants.update(exec_title for exec_title in executives if exec_title in words)
        
        return list(participants)

    def _format_panel_input(self, todo: Dict[str, Any], participants: List[str]) -> Dict[str, Any]:
        """Format todo into panel discussion input."""
        return {
            "timestamp": datetime.now().strftime("%Y%m%dT%H%M"),
            "invited": participants,
            "inquiry": todo['task']
        }

    def process_todos(self) -> List[Dict[str, str]]:
        """Process all todos and run panel discussions for relevant ones."""
        # Get todos from store
        namespace = ("todo", self.user_id)
        todos = self.store.search(namespace)
        
        results = []
        
        for todo_item in todos:
            todo = todo_item.value
            
            # Skip if todo is already completed
            if todo.get('status') == 'Done':
                continue
                
            # Extract participants
            participants = self._extract_participants_from_todo(todo)
            
            # Skip if no executives are involved
            if not participants:
                continue
                
            # Format input for panel discussion
            panel_input = self._format_panel_input(todo, participants)
            
            # Run panel discussion
            summary = self.panel_workflow.run(panel_input['inquiry'])
            
            # Update todo with discussion results
            todo['status'] = 'Done'
            todo['solutions'].append(f"Panel Discussion Summary: {summary}")
            
            # Update store
            self.store.put(namespace, todo_item.key, todo)
            
            # Add to results
            results.append({
                "task": todo['task'],
                "participants": ", ".join(participants),
                "summary": summary
            })
        
        return results 