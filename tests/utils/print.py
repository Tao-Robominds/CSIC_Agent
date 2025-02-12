from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.store.base import BaseStore
from typing import Union, Dict, Any

def print_todo_items(todos):
    """Helper function to print todo items in a readable format"""
    for todo in todos:
        print("\nToDo Item:")
        print(f"  Task: {todo.value['task']}")
        print(f"  Time to Complete: {todo.value.get('time_to_complete', 'Not specified')} minutes")
        
        # Handle deadline that could be string or datetime
        deadline = todo.value.get('deadline')
        if deadline:
            if isinstance(deadline, datetime):
                deadline_str = deadline.strftime('%Y-%m-%d %H:%M')
            else:
                deadline_str = deadline
            print(f"  Deadline: {deadline_str}")
        else:
            print("  Deadline: Not specified")
            
        print(f"  Solutions:")
        for solution in todo.value.get('solutions', []):
            print(f"    - {solution}")
        print(f"  Status: {todo.value.get('status', 'Not specified')}")
        
        # Only print updated_at if it exists
        if hasattr(todo, 'updated_at'):
            print(f"  Last Updated: {todo.updated_at}")
        print("-" * 50)


def print_command(command):
    """Helper function to print command in a readable format"""
    if not command:
        print("\nCommand: No command information available")
        return
        
    print("\nUser Command:")
    print(f"  Name: {command.value.get('name', 'Not specified')}")
    print(f"  Location: {command.value.get('location', 'Not specified')}")
    print(f"  Job: {command.value.get('job', 'Not specified')}")
    print("  Connections:")
    for connection in command.value.get('connections', []):
        print(f"    - {connection}")
    print("  Interests:")
    for interest in command.value.get('interests', []):
        print(f"    - {interest}")
    print(f"  Last Updated: {command.updated_at}")
    print("-" * 50)


def print_instructions(instructions):
    """Helper function to print instructions in a readable format"""
    if not instructions:
        print("\nInstructions: No custom instructions available")
        return
        
    print("\nCustom Instructions:")
    print(f"  {instructions.value.get('memory', 'No instructions set')}")
    print(f"  Last Updated: {instructions.updated_at}")
    print("-" * 50)


def print_all_memory(store, user_id):
    """Print all memory types (Command, ToDos, Instructions) in a readable format"""
    print("\n========== MEMORY STATE ==========")
    
    # Print Command
    print("\n=== USER PROFILE ===")
    commands = store.search(("command", user_id))
    print_command(commands[0] if commands else None)
    
    # Print ToDos
    print("\n=== TODO ITEMS ===")
    todos = store.search(("todo", user_id))
    if todos:
        print_todo_items(todos)
    else:
        print("No ToDo items found")
    
    # Print Instructions
    print("\n=== CUSTOM INSTRUCTIONS ===")
    instructions = store.search(("instructions", user_id))
    print_instructions(instructions[0] if instructions else None)
    
    print("\n================================")


def print_chat_message(message):
    """Helper function to print regular chat messages"""
    if isinstance(message, HumanMessage):
        print("\nHuman:")
        print(f"  {message.content}")
    elif isinstance(message, AIMessage):
        print("\nAssistant:")
        print(f"  {message.content}")
    elif isinstance(message, SystemMessage):
        print("\nSystem:")
        print(f"  {message.content}")
    print("-" * 50)


def print_messages(messages):
    """Print all messages in the conversation"""
    print("\n========== CONVERSATION ==========")
    for message in messages:
        print_chat_message(message)
    print("================================")


def print_memory_store(store: BaseStore, config: Union[Dict[str, Any], str]):
    """Print all memories for a given user.
    
    Args:
        store: The memory store containing user data
        config: Either a config dict with user_id or a user_id string
    """
    # Handle both config dict and direct user_id string
    user_id = config["configurable"]["user_id"] if isinstance(config, dict) else config
    
    print("\n=== Current Memory Store ===")
    
    # Print Command
    print("\nPROFILE:")
    namespace = ("command", user_id)
    memories = store.search(namespace)
    if memories:
        print(f"  {memories[0].value}")
    else:
        print("  No command found")
    
    # Print Todo List
    print("\nTODO LIST:")
    namespace = ("todo", user_id)
    memories = store.search(namespace)
    if memories:
        for mem in memories:
            print(f"  {mem.value}")
    else:
        print("  No todos found")
    
    # Print Instructions
    print("\nINSTRUCTIONS:")
    namespace = ("instructions", user_id)
    memories = store.search(namespace)
    if memories:
        print(f"  {memories[0].value}")
    else:
        print("  No instructions found")
    
    print("\n=========================")


def print_panel_results(results):
    """Helper function to print panel discussion results in a readable format"""
    if not results:
        print("\nNo panel discussion results available")
        return
        
    print("\nPanel Discussion Results:")
    print("=" * 50)
    
    for result in results:
        print(f"\nTask: {result['task']}")
        print("-" * 30)
        print(f"Participants: {result['participants']}")
        print("\nDiscussion Summary:")
        print(f"{result['summary']}")
        print("-" * 50) 