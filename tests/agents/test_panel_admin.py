import warnings
warnings.filterwarnings("ignore")

from pytest import mark
from backend.agents.panel_admin import PanelAdminAgent as Agent


@mark.agent
@mark.panel_admin
class TestAgent:
    def test_agent_behaviours(self):
        user_id = "Jack"
        request = "Hi, Donnie, I want to know the budget of the company."
        agent_instance = Agent(user_id, request)
        result = agent_instance.actor()
        print(result)
        assert result is not None

    def test_agent_trigger_behaviours(self):
        user_id = "Jack"
        request = "How can we improve the company?"
        agent_instance = Agent(user_id, request)
        result = agent_instance.actor()
        print(result)
        assert result is not None