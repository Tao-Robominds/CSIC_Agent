import warnings
warnings.filterwarnings("ignore")

from pytest import mark
from backend.agents.cmo import CMOAgent as Agent


@mark.agent
@mark.cmo
class TestAgent:
    def test_agent_behaviours(self):
        user_id = "boringtao"
        request = "Who are you?"
        agent_instance = Agent(user_id, request)
        result = agent_instance.actor()
        print(result)
        assert result is not None