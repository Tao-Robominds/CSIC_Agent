import os
import json
import requests
from typing import Optional
from dataclasses import dataclass
from backend.agents.utils.stream_parser import Stream_Parser

@dataclass
class CAgentConfig:
    """Configuration for C-level agents."""
    role: str
    api_key: str
    title: str
    url: str = "http://api.dify.ai.mh5.uk:8080/v1/chat-messages"
    user: str = "CSIC"

# Predefined configurations for different C-level roles
AGENT_CONFIGS = {
    "CEO": CAgentConfig(
        role="CEO",
        api_key="app-tbjntqmQZARupc7AfFG2ilM7",
        title="Chief Executive Officer"
    ),
    "CMO": CAgentConfig(
        role="CMO",
        api_key="app-6wjC79xDiqdhg2ItB8JUclKa",
        title="Chief Marketing Officer"
    ),
    "CFO": CAgentConfig(
        role="CFO",
        api_key="app-YE529Z2MzJ2DlAKti7AOuwz6",
        title="Chief Financial Officer"
    )
}

class CAgent:
    """Base class for C-level executive agents."""
    
    def __init__(self, user_id: str, request: Optional[str], config: CAgentConfig):
        """Initialize the C-level agent.
        
        Args:
            user_id: The user ID for the agent
            request: The request to process
            config: Configuration for this specific C-level role
        """
        self.user_id = user_id
        self.request = request
        self.config = config
        
        if not config.api_key:
            raise ValueError(f"API key not set for {config.title}")
        
        self.headers = {
            'Authorization': 'Bearer ' + config.api_key,
            'Content-Type': 'application/json',
        }

    def perceiver(self) -> str:
        """Process the incoming request."""
        return str(self.request) if self.request else ""

    def actor(self) -> str:
        """Generate a response based on the request."""
        query = self.perceiver()

        data = {
            "inputs": {},
            "query": query,
            "response_mode": "streaming",
            "conversation_id": "",
            "user": self.config.user
        }

        response = requests.post(
            self.config.url, 
            headers=self.headers, 
            data=json.dumps(data)
        )
        json_str = Stream_Parser(response.text).parser()
        response_data = json.loads(json_str)
        result = response_data.get('thought', 'Result not found')
        
        return result

    @classmethod
    def create(cls, role: str, user_id: str, request: Optional[str] = None) -> 'CAgent':
        """Factory method to create a C-level agent of a specific role.
        
        Args:
            role: The role of the C-level executive (e.g., "CEO", "CMO")
            user_id: The user ID for the agent
            request: The request to process
            
        Returns:
            A configured CAgent instance for the specified role
        """
        config = AGENT_CONFIGS.get(role.upper())
        if not config:
            raise ValueError(f"Unknown C-level role: {role}")
        
        return cls(user_id, request, config) 