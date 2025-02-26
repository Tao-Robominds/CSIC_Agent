import os
import json
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
    timeout: int = 180  # Increased timeout to 180 seconds

# Predefined configurations for different engineering roles
AGENT_CONFIGS = {
    "PROJECT_MANAGER": CSICAgentConfig(
        role="PROJECT_MANAGER",
        api_key="app-XL7sCu8g52I2J9nabjCrBuvB",
        title="Project Manager",
        timeout=180  # Explicitly set timeout for each role
    ),
    "SENIOR_ENGINEER": CSICAgentConfig(
        role="SENIOR_ENGINEER",
        api_key="app-x87uPTk0vnLEAIxxuZ0LKfgV",
        title="Senior Engineer",
        timeout=180
    ),
    "PRINCIPAL_ENGINEER": CSICAgentConfig(
        role="PRINCIPAL_ENGINEER",
        api_key="app-UpiwWQkSq4v2vd8yDlZVQoUM",
        title="Principal Engineer",
        timeout=180
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
            "conversation_id": None  # Added to ensure new conversation each time
        }

        try:
            response = requests.post(
                self.config.url, 
                headers=self.headers, 
                json=data,
                timeout=self.config.timeout,
                stream=False  # Explicitly set stream to False
            )
            
            # First check if we can parse the response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                print(f"Raw response content: {response.text}")
                raise Exception("Invalid JSON response from API")

            # Then check for error status
            if response.status_code >= 400:
                error_msg = response_data.get('message', 'Unknown error')
                raise Exception(f"API Error: {error_msg}")
            
            # Extract response from workflow output
            if "data" in response_data:
                workflow_data = response_data["data"]
                
                # Check for error status first
                if workflow_data.get("status") == "failed":
                    error = workflow_data.get("error", "Unknown workflow error")
                    raise Exception(f"Workflow failed: {error}")
                
                # Try to get output from different possible locations
                if "outputs" in workflow_data:
                    outputs = workflow_data["outputs"]
                    if isinstance(outputs, dict):
                        if "answer" in outputs:
                            return outputs["answer"]
                        if "text" in outputs:
                            return outputs["text"]
                        return str(outputs)
                    return str(outputs)
                
                # If no outputs but workflow succeeded
                if workflow_data.get("status") == "succeeded":
                    if "message" in workflow_data:
                        return workflow_data["message"]
                    return str(workflow_data)
            
            # If we get here, try to find any usable response
            for key in ["answer", "response", "text", "message"]:
                if key in response_data:
                    return response_data[key]
            
            raise Exception("No valid response found in workflow output")
                
        except requests.exceptions.Timeout:
            raise Exception(f"Request timed out after {self.config.timeout} seconds")
        except requests.exceptions.RequestException as e:
            print(f"Error making request: {str(e)}")
            print(f"Response content: {response.text if 'response' in locals() else 'No response'}")
            raise Exception(f"Request failed: {str(e)}")
        except Exception as e:
            if "response" in locals():
                print(f"Response content: {response.text}")
            raise e

    @classmethod
    def create(cls, role: str, user_id: str, request: Optional[str] = None) -> 'CSICAgent':
        """Factory method to create a CSIC agent of a specific role."""
        config = AGENT_CONFIGS.get(role.upper())
        if not config:
            raise ValueError(f"Unknown engineering role: {role}")
        
        return cls(user_id, request, config) 