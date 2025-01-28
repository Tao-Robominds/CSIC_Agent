import warnings
from pytest import mark
from backend.components.gpt_parser import GPTRequest as Request, GPTComponent as Component


@mark.component
@mark.gpt_parser
class TestComponent:
    def test_component_behaviours(self):
        messages = [
            {"role": "system", "content": (
                "You are a strategic business consultant. Your task is to synthesize the discussion "
                "between a CMO and CPO into a concrete, actionable plan. Focus on key agreements "
                "and resolve any conflicts in a practical way."
            )},
            {"role": "user", "content": (
                "Original task: Develop a go-to-market strategy for selling beers in the UK market."
                "Discussion summary:\n" + 
                "CMO: We should focus on the premium market segment.\n" +
                "CPO: We should also consider the budget-conscious market segment.\n" +
                "Format the plan with clear steps, responsibilities, and expected outcomes."
            )}
        ]
        # Test with a valid query
        request = Request(messages=messages)
        component = Component(request)
        response = component.actor()

        print(response["response"])
        assert response["status"] == "success"