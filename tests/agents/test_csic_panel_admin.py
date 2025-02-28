import warnings
warnings.filterwarnings("ignore")

from pytest import mark
from backend.agents.csic_panel_admin import PanelAdminAgent as Agent


@mark.agent
@mark.csic_panel_admin
class TestAgent:
    def test_agent_behaviours(self):
        user_id = "CSIC"
        request = "How can we develop an optimal maintenance strategy for the Islington Tunnel that balances operational efficiency, safety, and cost-effectiveness, while also considering the long-term sustainability of the infrastructure? What are the estimated costs associated with this strategy, and what assumptions are we making about the current condition of the tunnel and future usage?"
        agent_instance = Agent(user_id, request)
        result = agent_instance.actor()
        print(result)
        assert result is not None