import pytest
from backend.workflows.cot_master import (
    run_project_manager,
    run_senior_engineer,
    run_principal_engineer
)

@pytest.mark.cot_master
class TestCOTMaster:
    def test_project_manager(self):
        """Test Project Manager's response."""
        state = {
            "messages": [
                "How should we implement a smart bridge monitoring system?"
            ]
        }
        
        result = run_project_manager(state, {})
        assert "messages" in result
        assert isinstance(result["messages"][-1], str)
        assert result["messages"][-1].startswith("Project Manager:")
        print("\nProject Manager Response:", result["messages"][-1])

    def test_senior_engineer(self):
        """Test Senior Engineer's response."""
        state = {
            "messages": [
                "How should we implement a smart bridge monitoring system?"
            ]
        }
        
        result = run_senior_engineer(state, {})
        assert "messages" in result
        assert isinstance(result["messages"][-1], str)
        assert result["messages"][-1].startswith("Senior Engineer:")
        print("\nSenior Engineer Response:", result["messages"][-1])

    def test_principal_engineer(self):
        """Test Principal Engineer's response."""
        state = {
            "messages": [
                "How should we implement a smart bridge monitoring system?"
            ]
        }
        
        result = run_principal_engineer(state, {})
        assert "messages" in result
        assert isinstance(result["messages"][-1], str)
        assert result["messages"][-1].startswith("Principal Engineer:")
        print("\nPrincipal Engineer Response:", result["messages"][-1])

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"]) 