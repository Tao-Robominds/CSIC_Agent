import pytest
from datetime import datetime
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from backend.workflows.panel_master import (
    panel_master, 
    update_todos, 
    update_instructions,
    route_message,
    ToDo,
    END,
    graph
)
from langgraph.store.memory import InMemoryStore
from backend.store.redis_store import RedisStore
from backend.store.redis_config import get_redis_config
from tests.utils.print import (
    print_todo_items,
    print_instructions,
    print_all_memory,
    print_messages
)


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def redis_store():
    config = get_redis_config()
    return RedisStore(**config)


@pytest.fixture
def config():
    return {
        "configurable": {
            "user_id": "CSIC"
        }
    }


@pytest.fixture
def test_user_config():
    return {
        "configurable": {
            "user_id": "test_user"
        }
    }


@pytest.mark.agent
@pytest.mark.panel_master
class TestPanelMaster:
    # Initialize the model once for all tests
    model = ChatOpenAI(model="gpt-4o", temperature=0)

    def test_panel_master_basic(self, store, config):
        state = {
            "messages": [
                HumanMessage(content="Hello, how are you?")
            ]
        }
        
        result = panel_master(state, config)
        assert "messages" in result
        assert len(result["messages"]) == 1

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
                HumanMessage(content="Please always add deadlines to my tasks and break them down into smaller tasks"),
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
        # Create and store a todo
        todo = ToDo(
            task="Finish project",
            status="Active",
            solutions=["Break into smaller tasks", "Set milestones"]
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
        
        result = panel_master(state, config)
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
        
        result = route_message(state, config)
        assert result == END

    @pytest.mark.redis
    def test_redis_connection(self, redis_store):
        """Test Redis Cloud connection"""
        try:
            redis_store.redis.ping()
            assert True
        except Exception as e:
            pytest.fail(f"Redis connection failed: {str(e)}")

    @pytest.mark.redis
    def test_redis_todo_creation(self, redis_store, test_user_config):
        """Test todo creation with Redis Cloud storage"""
        # Test adding a todo
        todo_messages = {
            "messages": [
                HumanMessage(content="Add a todo: Complete the Redis integration by end of week")
            ]
        }
        
        result = graph.invoke(todo_messages, config=test_user_config)
        assert "messages" in result
        
        # Check if todo was stored
        todos = redis_store.search(("todo", test_user_config["configurable"]["user_id"]))
        assert len(todos) > 0
        
        # Verify todo content
        todo = todos[0]
        assert "task" in todo.value
        assert "status" in todo.value
        assert todo.value["status"] == "Active"

    @pytest.mark.redis
    def test_redis_instructions_update(self, redis_store, test_user_config):
        """Test instructions update with Redis Cloud storage"""
        # Test adding instructions
        instruction_messages = {
            "messages": [
                HumanMessage(content="Update instructions: Always add deadlines to tasks and prioritize them")
            ]
        }
        
        result = graph.invoke(instruction_messages, config=test_user_config)
        assert "messages" in result
        
        # Check if instructions were stored
        instructions = redis_store.search(("instructions", test_user_config["configurable"]["user_id"]))
        assert len(instructions) > 0
        
        # Verify instructions content
        instruction = instructions[0]
        assert "memory" in instruction.value

    @pytest.mark.redis
    def test_redis_cleanup(self, redis_store, test_user_config):
        """Clean up test data from Redis after tests"""
        user_id = test_user_config["configurable"]["user_id"]
        
        # Clean up todos
        todos = redis_store.search(("todo", user_id))
        for todo in todos:
            redis_store.delete(("todo", user_id), todo.key)
            
        # Clean up instructions
        instructions = redis_store.search(("instructions", user_id))
        for instruction in instructions:
            redis_store.delete(("instructions", user_id), instruction.key)
            
        # Verify cleanup
        assert len(redis_store.search(("todo", user_id))) == 0
        assert len(redis_store.search(("instructions", user_id))) == 0