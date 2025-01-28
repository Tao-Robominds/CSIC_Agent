import warnings
warnings.filterwarnings("ignore")

from pytest import mark
from backend.agents.ceo import CEOAgent as Agent


@mark.agent
@mark.ceo
class TestAgent:
    def test_agent_behaviours(self):
        user_id = "Jack"
        request = "Who are you?"
        agent_instance = Agent(user_id, request)
        result = agent_instance.actor()
        print(result)
        assert result is not None