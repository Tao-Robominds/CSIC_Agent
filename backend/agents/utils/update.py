import uuid
from datetime import datetime
import re
from typing import List, Dict, Any, Optional

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
from backend.agents.utils.todo_handlers import handle_todo_operation, handle_todo_update

def update_command(state: MessagesState, config: RunnableConfig, store: Optional[BaseStore], model: BaseChatModel):
    """Reflect on the chat history and update the command memory collection."""
    
    if not store:
        return {"messages": [SystemMessage(content="Error: No store provided in configuration.")]}
    
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

def update_todos(state: MessagesState, config: RunnableConfig, store: Optional[BaseStore], model: BaseChatModel) -> Dict:
    """Main function to handle todo updates."""
    if not store:
        return {"messages": [SystemMessage(content="Error: No store provided in configuration.")]}
    
    try:
        # Setup
        configurable = Configuration.from_runnable_config(config)
        namespace = ("todo", configurable.user_id)
        last_message = state['messages'][-2].content.lower()
        tool_calls = state['messages'][-1].tool_calls

        # Handle different commands
        if any(phrase in last_message for phrase in ["clear all tasks", "delete all tasks", "remove all tasks"]):
            return handle_todo_operation(namespace, store, tool_calls, "clear_all")
            
        if any(phrase in last_message for phrase in ["remove task", "delete task", "clear task"]):
            numbers = [int(num) for num in re.findall(r'\d+', last_message)]
            if numbers:
                return handle_todo_operation(namespace, store, tool_calls, "remove_specific", numbers=numbers)
                
        if any(phrase in last_message for phrase in ["clear completed", "remove done", "clean up", "delete finished"]):
            return handle_todo_operation(namespace, store, tool_calls, "clear_completed")
            
        # Default: handle todo update/addition
        return handle_todo_update(namespace, store, state, model)

    except Exception as e:
        print(f"Error in update_todos: {str(e)}")
        raise

def update_instructions(state: MessagesState, config: RunnableConfig, store: Optional[BaseStore], model: BaseChatModel):
    """Reflect on the chat history and update the instructions memory collection."""
    
    if not store:
        return {"messages": [SystemMessage(content="Error: No store provided in configuration.")]}
    
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