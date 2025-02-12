from typing import List, Dict
import uuid
from langgraph.store.base import BaseStore
from langgraph.graph import MessagesState
from langchain_core.messages import SystemMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import merge_message_runs

from backend.agents.utils.spy import Spy
from backend.agents.utils.extract_tool_info import extract_tool_info
from backend.agents.utils.schemas import ToDo
from backend.agents.prompts.panel_master_prompts import TRUSTCALL_INSTRUCTION
from trustcall import create_extractor
from datetime import datetime

def handle_todo_operation(
    namespace: tuple, 
    store: BaseStore, 
    tool_calls: List[Dict],
    operation: str,
    **kwargs
) -> Dict:
    """Generic handler for todo operations."""
    todos = store.search(namespace)
    removed_tasks = []
    todos_to_keep = []

    match operation:
        case "clear_all":
            # Remove all tasks
            removed_tasks = [todo.value.get('task', 'Unknown task') for todo in todos]
            message = "Removed all tasks"

        case "remove_specific":
            # Remove specific tasks by number
            numbers = kwargs.get('numbers', [])
            indices = [n - 1 for n in numbers]
            
            for i, todo in enumerate(todos):
                todo_data = todo.value if hasattr(todo, 'value') else todo
                if i not in indices:
                    todos_to_keep.append(todo)
                else:
                    removed_tasks.append(todo_data.get('task', 'Unknown task'))
            message = f"Removed tasks: {', '.join(removed_tasks)}"

        case "clear_completed":
            # Keep only active tasks
            for todo in todos:
                if todo.value.get('status', '') != 'Done':
                    todos_to_keep.append(todo)
                else:
                    removed_tasks.append(todo.value.get('task', 'Unknown task'))
            message = f"Removed {len(removed_tasks)} completed tasks"

        case _:
            raise ValueError(f"Unknown operation: {operation}")

    # Update store
    for todo in todos:
        store.delete(namespace, todo.key)
    
    for todo in todos_to_keep:
        store.put(namespace, str(uuid.uuid4()), todo.value)

    return {
        "messages": [{
            "role": "tool",
            "content": message,
            "tool_call_id": tool_calls[0]['id']
        }]
    }

def handle_todo_update(namespace: tuple, store: BaseStore, state: MessagesState, model: BaseChatModel) -> Dict:
    """Handle updating or adding todos."""
    todos = store.search(namespace)
    
    # Format for Trustcall
    TRUSTCALL_INSTRUCTION_FORMATTED = TRUSTCALL_INSTRUCTION.format(
        time=datetime.now().isoformat()
    )
    updated_messages = list(merge_message_runs(
        messages=[SystemMessage(content=TRUSTCALL_INSTRUCTION_FORMATTED)] + state["messages"][:-1]
    ))

    # Create extractor
    spy = Spy()
    todo_extractor = create_extractor(
        model,
        tools=[ToDo],
        tool_choice="ToDo",
        enable_inserts=True
    ).with_listeners(on_end=spy)

    # Invoke extractor
    result = todo_extractor.invoke({
        "messages": updated_messages,
        "existing": [(todo.key, "ToDo", todo.value) for todo in todos] if todos else None
    })

    # Save results
    for r, rmeta in zip(result["responses"], result["response_metadata"]):
        store.put(namespace,
                rmeta.get("json_doc_id", str(uuid.uuid4())),
                r.model_dump(mode="json"))

    tool_calls = state['messages'][-1].tool_calls
    todo_update_msg = extract_tool_info(spy.called_tools, "ToDo")
    return {"messages": [{"role": "tool", "content": todo_update_msg, "tool_call_id":tool_calls[0]['id']}]} 