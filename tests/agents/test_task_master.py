import pytest
from datetime import datetime
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from backend.agents.task_master import (
    task_master, 
    update_command, 
    update_todos, 
    update_instructions,
    route_message,
    Command,
    ToDo,
    END
)
from langgraph.store.memory import InMemoryStore
from tests.agents.utils.print import (
    print_todo_items,
    print_command,
    print_instructions,
    print_all_memory,
    print_messages
)


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def config():
    return {
        "configurable": {
            "user_id": "Jack"
        }
    }


@pytest.mark.agent
@pytest.mark.task_master
class TestTaskMaistro:
    # Initialize the model once for all tests
    model = ChatOpenAI(model="gpt-4o", temperature=0)

    def test_task_master_basic(self, store, config):
        state = {
            "messages": [
                HumanMessage(content="Hello, how are you?")
            ]
        }
        
        result = task_master(state, config, store)
        assert "messages" in result
        assert len(result["messages"]) == 1

    def test_command_update(self, store, config):
        tool_call = {
            "id": "call_123",
            "name": "UpdateMemory",
            "args": {"update_type": "user"}
        }
        
        message = AIMessage(
            content="I've noted that information.",
            additional_kwargs={
                "tool_calls": [tool_call]
            }
        )
        message.tool_calls = [tool_call]  # Add tool_calls directly to message
        
        state = {
            "messages": [
                HumanMessage(content="Hi, I'm Jack. I want to talk to my CEO and CMO about how to do Facebook compaigns"),
                SystemMessage(content="I'll update your command"),
                message
            ]
        }
        
        result = update_command(state, config, store, self.model)
        print(result)
        assert "messages" in result
        assert result["messages"][0]["role"] == "tool"
        assert result["messages"][0]["tool_call_id"] == tool_call["id"]
        
        # After the test, print the command
        commands = store.search(("command", config["configurable"]["user_id"]))
        print_command(commands[0] if commands else None)

    def test_todo_update(self, store, config):
        tool_call = {
            "id": "call_456",
            "name": "UpdateMemory",
            "args": {"update_type": "todo"}
        }
        
        message = AIMessage(
            content="I'll add that task.",
            additional_kwargs={
                "tool_calls": [tool_call]
            }
        )
        message.tool_calls = [tool_call]  # Add tool_calls directly to message
        
        state = {
            "messages": [
                HumanMessage(content="I need to finish the project by next week"),
                SystemMessage(content="I'll add that to your todo list"),
                message
            ]
        }
        
        result = update_todos(state, config, store, self.model)
        assert "messages" in result
        assert result["messages"][0]["role"] == "tool"
        assert result["messages"][0]["tool_call_id"] == tool_call["id"]
        
        # After the test, print the todos
        todos = store.search(("todo", config["configurable"]["user_id"]))
        print_todo_items(todos)

    def test_instructions_update(self, store, config):
        tool_call = {
            "id": "call_789",
            "name": "UpdateMemory",
            "args": {"update_type": "instructions"}
        }
        
        message = AIMessage(
            content="I'll update my instructions.",
            additional_kwargs={
                "tool_calls": [tool_call]
            }
        )
        message.tool_calls = [tool_call]  # Add tool_calls directly to message
        
        state = {
            "messages": [
                HumanMessage(content="Please always add deadlines to my tasks, break them down into smaller tasks and give all the connections (CEO, CFO, CMO, etc.) specific guidance"),
                SystemMessage(content="I'll update my instructions"),
                message
            ]
        }
        
        result = update_instructions(state, config, store, self.model)
        assert "messages" in result
        assert result["messages"][0]["role"] == "tool"
        assert result["messages"][0]["tool_call_id"] == tool_call["id"]
        
        # After the test, print the instructions
        instructions = store.search(("instructions", config["configurable"]["user_id"]))
        print_instructions(instructions[0] if instructions else None)

    def test_end_to_end(self, store, config):
        # Create and store a command
        command = Command(
            name="John Doe",
            location="New York",
            job="Software Engineer",
            connections=["CEO", "CTO"],
            interests=["AI", "Machine Learning"]
        )
        store.put(("command", config["configurable"]["user_id"]), "command_1", command.model_dump())

        # Create and store a todo
        todo = ToDo(
            task="Finish project",
            time_to_complete=120,
            deadline=datetime.now(),
            solutions=["Break into smaller tasks", "Set milestones"],
            status="not started"
        )
        store.put(("todo", config["configurable"]["user_id"]), "task_1", todo.model_dump())

        # Create and store instructions
        instructions = {"memory": "Always break down tasks and set clear deadlines"}
        store.put(("instructions", config["configurable"]["user_id"]), "user_instructions", instructions)

        state = {
            "messages": [
                HumanMessage(content="I need to finish the project by next week")
            ]
        }
        
        result = task_master(state, config, store)
        assert "messages" in result
        
        # Print all memory after the test
        print_all_memory(store, config["configurable"]["user_id"])

    def test_route_message_no_tool_calls(self, store, config):
        state = {
            "messages": [
                HumanMessage(content="Hello, how are you?"),
                AIMessage(content="Just a regular message")
            ]
        }
        
        # Print the conversation
        print_messages(state["messages"])
        
        result = route_message(state, config, store)
        assert result == END