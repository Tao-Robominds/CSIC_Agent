import uuid
from datetime import datetime
import re

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import merge_message_runs, SystemMessage, HumanMessage
from langchain_core.language_models import BaseChatModel
from langgraph.graph import MessagesState
from langgraph.store.base import BaseStore
from trustcall import create_extractor

from backend.agents.utils.spy import Spy
from backend.agents.utils.extract_tool_info import extract_tool_info
from backend.agents.utils.schemas import Command, ToDo
from backend.agents.utils.configuration import Configuration
from backend.agents.prompts.task_master_prompts import TRUSTCALL_INSTRUCTION, CREATE_INSTRUCTIONS

def update_command(state: MessagesState, config: RunnableConfig, store: BaseStore, model: BaseChatModel):
    """Reflect on the chat history and update the command memory collection."""
    
    # Get the user ID from the config
    configurable = Configuration.from_runnable_config(config)
    user_id = configurable.user_id

    # Define the namespace for the memories
    namespace = ("command", user_id)

    # Retrieve the most recent memories for context
    existing_items = store.search(namespace)

    # Format the existing memories for the Trustcall extractor
    tool_name = "Command"
    existing_memories = ([(existing_item.key, tool_name, existing_item.value)
                          for existing_item in existing_items]
                          if existing_items
                          else None
                        )

    # Format the instruction with current time
    TRUSTCALL_INSTRUCTION_FORMATTED = TRUSTCALL_INSTRUCTION.format(
        time=datetime.now().isoformat()
    )
    updated_messages = list(merge_message_runs(
        messages=[SystemMessage(content=TRUSTCALL_INSTRUCTION_FORMATTED)] + state["messages"][:-1]
    ))

    # Initialize the spy for visibility into the tool calls made by Trustcall
    spy = Spy()
    
    # Create the Trustcall extractor for updating the command
    command_extractor = create_extractor(
        model,
        tools=[Command],
        tool_choice="Command",
        enable_inserts=True
    ).with_listeners(on_end=spy)

    # Invoke the extractor
    result = command_extractor.invoke({"messages": updated_messages, 
                                     "existing": existing_memories})

    # Save the memories from Trustcall to the store
    for r, rmeta in zip(result["responses"], result["response_metadata"]):
        store.put(namespace,
                  rmeta.get("json_doc_id", str(uuid.uuid4())),
                  r.model_dump(mode="json"),
            )
    tool_calls = state['messages'][-1].tool_calls
    # Extract the changes made by Trustcall and add them to the ToolMessage
    command_update_msg = extract_tool_info(spy.called_tools, "Command")
    return {"messages": [{"role": "tool", "content": command_update_msg, "tool_call_id":tool_calls[0]['id']}]}

def update_todos(state: MessagesState, config: RunnableConfig, store: BaseStore, model: BaseChatModel):
    """Reflect on the chat history and update the todo memory collection."""
    
    # Get the user ID from the config
    configurable = Configuration.from_runnable_config(config)
    user_id = configurable.user_id

    # Define the namespace for the memories
    namespace = ("todo", user_id)
    
    # Get existing todos
    existing_todos = store.search(namespace)
    
    # Check if this is a task removal request
    last_message = state['messages'][-2].content.lower()  # Get user's last message
    
    # Handle task removal by number
    if any(phrase in last_message for phrase in ["remove task", "delete task"]):
        # Extract numbers from the message
        numbers = [int(num) for num in re.findall(r'\d+', last_message)]
        
        if numbers and existing_todos:
            # Convert to 0-based index
            indices = [n - 1 for n in numbers]
            # Create a list of tasks to keep
            todos_to_keep = []
            removed_tasks = []
            
            for i, todo in enumerate(existing_todos):
                if i not in indices:
                    todos_to_keep.append(todo)
                else:
                    removed_tasks.append(todo.value['task'])
            
            # Remove all existing todos
            for todo in existing_todos:
                store.delete(namespace, todo.key)
            
            # Add back the ones we want to keep
            for todo in todos_to_keep:
                store.put(namespace, str(uuid.uuid4()), todo.value)
            
            tool_calls = state['messages'][-1].tool_calls
            return {
                "messages": [{
                    "role": "tool",
                    "content": f"Removed tasks: {', '.join(removed_tasks)}",
                    "tool_call_id": tool_calls[0]['id']
                }]
            }
    
    # Check if this is a cleanup request
    is_cleanup = any(phrase in last_message for phrase in [
        "clear completed", "remove done", "clean up", "delete finished"
    ])

    if is_cleanup:
        # Filter out completed tasks
        active_todos = [
            todo for todo in existing_todos 
            if todo.value.get('status', '') != 'Done'
        ]
        
        # Remove all existing todos
        for todo in existing_todos:
            store.delete(namespace, todo.key)
        
        # Add back only active todos
        for todo in active_todos:
            store.put(namespace, str(uuid.uuid4()), todo.value)
        
        removed_count = len(existing_todos) - len(active_todos)
        tool_calls = state['messages'][-1].tool_calls
        return {
            "messages": [{
                "role": "tool", 
                "content": f"Removed {removed_count} completed tasks", 
                "tool_call_id": tool_calls[0]['id']
            }]
        }
    
    # For existing todos without timestamps, add them
    current_time = datetime.now()
    updated_todos = []
    
    for todo in existing_todos:
        todo_data = todo.value
        if not isinstance(todo_data, dict):
            continue
            
        # Ensure created_at exists
        if 'created_at' not in todo_data:
            todo_data['created_at'] = current_time.isoformat()
            
        # Create a proper ToDo object
        todo_obj = ToDo(
            task=todo_data.get('task', ''),
            status=todo_data.get('status', 'Active'),
            created_at=todo_data.get('created_at', current_time),
            completed_at=todo_data.get('completed_at'),
            time_to_complete=todo_data.get('time_to_complete'),
            solutions=todo_data.get('solutions')
        )
        
        # Store the updated todo
        store.delete(namespace, todo.key)
        store.put(namespace, str(uuid.uuid4()), todo_obj.model_dump())
        updated_todos.append(todo_obj)
    
    # Format the existing memories for the Trustcall extractor
    tool_name = "ToDo"
    existing_memories = ([(existing_item.key, tool_name, existing_item.value)
                          for existing_item in existing_todos]
                          if existing_todos
                          else None
                        )

    # Format the instruction with current time
    TRUSTCALL_INSTRUCTION_FORMATTED = TRUSTCALL_INSTRUCTION.format(
        time=datetime.now().isoformat()
    )
    updated_messages = list(merge_message_runs(
        messages=[SystemMessage(content=TRUSTCALL_INSTRUCTION_FORMATTED)] + state["messages"][:-1]
    ))

    # Initialize the spy for visibility into the tool calls made by Trustcall
    spy = Spy()
    
    # Create the Trustcall extractor for updating the ToDo list 
    todo_extractor = create_extractor(
        model,
        tools=[ToDo],
        tool_choice=tool_name,
        enable_inserts=True
    ).with_listeners(on_end=spy)

    # Invoke the extractor
    result = todo_extractor.invoke({"messages": updated_messages, 
                                  "existing": existing_memories})

    # Save the memories from Trustcall to the store
    for r, rmeta in zip(result["responses"], result["response_metadata"]):
        store.put(namespace,
                  rmeta.get("json_doc_id", str(uuid.uuid4())),
                  r.model_dump(mode="json"),
            )
        
    # Extract the changes made by Trustcall and add them to the ToolMessage
    tool_calls = state['messages'][-1].tool_calls
    todo_update_msg = extract_tool_info(spy.called_tools, tool_name)
    return {"messages": [{"role": "tool", "content": todo_update_msg, "tool_call_id":tool_calls[0]['id']}]}

def update_instructions(state: MessagesState, config: RunnableConfig, store: BaseStore, model: BaseChatModel):
    """Reflect on the chat history and update the instructions memory collection."""
    
    # Get the user ID from the config
    configurable = Configuration.from_runnable_config(config)
    user_id = configurable.user_id
    
    namespace = ("instructions", user_id)

    existing_memory = store.get(namespace, "user_instructions")
        
    # Format the memory in the system prompt
    system_msg = CREATE_INSTRUCTIONS.format(
        current_instructions=existing_memory.value if existing_memory else None
    )
    new_memory = model.invoke(
        [SystemMessage(content=system_msg)] + 
        state['messages'][:-1] + 
        [HumanMessage(content="Please update the instructions based on the conversation")]
    )

    # Overwrite the existing memory in the store 
    key = "user_instructions"
    store.put(namespace, key, {"memory": new_memory.content})
    tool_calls = state['messages'][-1].tool_calls
    return {"messages": [{"role": "tool", "content": "updated instructions", "tool_call_id":tool_calls[0]['id']}]} 