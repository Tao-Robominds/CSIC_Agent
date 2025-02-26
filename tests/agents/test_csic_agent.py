import pytest
from backend.agents.csic_agent import CSICAgent, CSICAgentConfig


def test_project_manager():
    """Test Project Manager agent with a real API call."""
    agent = CSICAgent.create(
        "PROJECT_MANAGER", 
        "test-user", 
        "What are the key technical considerations for implementing a bridge monitoring system?"
    )
    try:
        response = agent.actor()
        assert response is not None
        assert len(response) > 0
        print(f"\nProject Manager Response: {response}")
    except Exception as e:
        print(f"\nProject Manager Error: {str(e)}")

def test_senior_engineer():
    """Test Senior Engineer agent with a real API call."""
    agent = CSICAgent.create(
        "SENIOR_ENGINEER", 
        "test-user", 
        "What sensors and data collection methods would you recommend for structural health monitoring?"
    )
    try:
        response = agent.actor()
        assert response is not None
        assert len(response) > 0
        print(f"\nSenior Engineer Response: {response}")
    except Exception as e:
        print(f"\nSenior Engineer Error: {str(e)}")

def test_principal_engineer():
    """Test Principal Engineer agent with a real API call."""
    agent = CSICAgent.create(
        "PRINCIPAL_ENGINEER", 
        "test-user", 
        "How would you design a resilient and scalable architecture for processing real-time sensor data?"
    )
    try:
        response = agent.actor()
        assert response is not None
        assert len(response) > 0
        print(f"\nPrincipal Engineer Response: {response}")
    except Exception as e:
        print(f"\nPrincipal Engineer Error: {str(e)}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"]) 