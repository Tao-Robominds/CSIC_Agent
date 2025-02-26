import requests
from typing import Optional
from dataclasses import dataclass

@dataclass
class CSICAgentConfig:
    """Configuration for CSIC engineering panel agents."""
    role: str
    api_key: str
    title: str
    url: str = "https://api.dify.ai/v1/workflows/run"
    user: str = "CSIC"
    timeout: int = 180

# Predefined configurations for different engineering roles
AGENT_CONFIGS = {
    "PROJECT_MANAGER": CSICAgentConfig(
        role="PROJECT_MANAGER",
        api_key="app-XL7sCu8g52I2J9nabjCrBuvB",
        title="Project Manager"
    ),
    "SENIOR_ENGINEER": CSICAgentConfig(
        role="SENIOR_ENGINEER",
        api_key="app-x87uPTk0vnLEAIxxuZ0LKfgV",
        title="Senior Engineer"
    ),
    "PRINCIPAL_ENGINEER": CSICAgentConfig(
        role="PRINCIPAL_ENGINEER",
        api_key="app-UpiwWQkSq4v2vd8yDlZVQoUM",
        title="Principal Engineer"
    )
}

class CSICAgent:
    """Base class for CSIC engineering panel agents."""
    
    def __init__(self, user_id: str, request: Optional[str], config: CSICAgentConfig):
        """Initialize the CSIC agent."""
        self.user_id = user_id
        self.request = request
        self.config = config
        
        if not config.api_key:
            raise ValueError(f"API key not set for {config.title}")
        
        self.headers = {
            'Authorization': f'Bearer {config.api_key}',
            'Content-Type': 'application/json',
        }

    def perceiver(self) -> str:
        """Process the incoming request."""
        return str(self.request) if self.request else ""

    def actor(self) -> str:
        """Generate a response based on the request using Dify workflow."""
        query = self.perceiver()

        data = {
            "inputs": {
                "inquiry": query
            },
            "response_mode": "blocking",
            "user": self.user_id,
            "conversation_id": None
        }

        try:
            response = requests.post(
                self.config.url, 
                headers=self.headers, 
                json=data,
                timeout=self.config.timeout,
                stream=False
            )
            
            response.raise_for_status()
            response_data = response.json()

            if "data" in response_data:
                workflow_data = response_data["data"]
                if "outputs" in workflow_data:
                    outputs = workflow_data["outputs"]
                    # Extract the actual text from the result
                    if isinstance(outputs, dict) and "result" in outputs:
                        return outputs["result"]
                    return str(outputs)
                if workflow_data.get("status") == "succeeded":
                    return str(workflow_data)
            
            return str(response_data)
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")

    @classmethod
    def create(cls, role: str, user_id: str, request: Optional[str] = None) -> 'CSICAgent':
        """Factory method to create a CSIC agent of a specific role."""
        config = AGENT_CONFIGS.get(role.upper())
        if not config:
            raise ValueError(f"Unknown engineering role: {role}")
        
        return cls(user_id, request, config) 