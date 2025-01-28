import pytest
from datetime import datetime
from backend.workflows.todo_panel_coordinator import TodoPanelCoordinator
from langgraph.store.memory import InMemoryStore
from tests.agents.utils.print import print_panel_results, print_todo_items

@pytest.fixture
def store():
    return InMemoryStore()

@pytest.fixture
def coordinator(store):
    return TodoPanelCoordinator(store, "test_user")

@pytest.mark.workflow
@pytest.mark.todo_panel_coordinator
def test_todo_panel_integration(store, coordinator):
    # Create a TodoItem with all necessary attributes
    todo = {
        "task": "Plan marketing campaign for new product launch",
        "time_to_complete": 120,
        "deadline": datetime.now(),
        "solutions": [
            "Schedule meeting with CEO to discuss budget",
            "Consult CMO about marketing strategy"
        ],
        "status": "not started"
    }
    
    # Create a mock TodoItem with updated_at attribute
    class TodoItem:
        def __init__(self, value, key):
            self.value = value
            self.key = key
            self.updated_at = datetime.now()
    
    store.put(("todo", "test_user"), "test_todo", todo)

    # Print initial todo using the proper TodoItem class
    print("\nInitial Todo:")
    print_todo_items([TodoItem(todo, 'test_todo')])
    
    # Process todos
    results = coordinator.process_todos()
    
    # Print results in readable format
    print_panel_results(results)
    
    # Print updated todo
    print("\nUpdated Todo:")
    updated_todo = store.get(("todo", "test_user"), "test_todo")
    print_todo_items([updated_todo])
    
    # Verify results
    assert len(results) == 1
    assert "CEO" in results[0]["participants"]
    assert "CMO" in results[0]["participants"]
    assert results[0]["task"] == todo["task"]
    assert results[0]["summary"]
    
    # Verify todo was updated
    assert updated_todo.value["status"] == "Done"
    assert any("Panel Discussion Summary" in solution 
              for solution in updated_todo.value["solutions"]) 