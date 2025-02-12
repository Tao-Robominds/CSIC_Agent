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
from backend.agents.utils.schemas import ToDo
from backend.agents.utils.configuration import Configuration
from backend.agents.prompts.panel_master_prompts import CREATE_INSTRUCTIONS
from backend.agents.utils.todo_handlers import handle_todo_operation, handle_todo_update

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
    """Update the instructions memory collection."""
    if not store:
        return {"messages": [SystemMessage(content="Error: No store provided in configuration.")]}
    
    configurable = Configuration.from_runnable_config(config)
    user_id = configurable.user_id
    namespace = ("instructions", user_id)

    existing_memory = store.get(namespace, "user_instructions")
    
    new_memory = model.invoke(
        [SystemMessage(content="Please update the instructions based on the conversation")] + 
        state['messages'][:-1] + 
        [HumanMessage(content="Please update the instructions based on the conversation")]
    )

    # Overwrite the existing memory in the store 
    key = "user_instructions"
    store.put(namespace, key, {"memory": new_memory.content})
    tool_calls = state['messages'][-1].tool_calls
    return {"messages": [{"role": "tool", "content": "updated instructions", "tool_call_id":tool_calls[0]['id']}]} 