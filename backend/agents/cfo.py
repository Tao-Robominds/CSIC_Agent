import os
import json
import requests
from backend.agents.utils.stream_parser import Stream_Parser


api_key = "app-YE529Z2MzJ2DlAKti7AOuwz6"
url = "http://api.dify.ai.mh5.uk:8080/v1/chat-messages"
if not api_key:
    raise ValueError("EXTRACT_API_KEY environment variable is not set.")

headers = {
    'Authorization': 'Bearer ' + api_key,
    'Content-Type': 'application/json',
}


class CFOAgent:
    def __init__(self, user_id, request):
        self.user_id = user_id
        self.request = request

    def perceiver(self):
        query = self.request
        return str(query)

    def actor(self):
        query = self.perceiver()

        conversation_id = ""  

        data = {
            "inputs": {},
            "query": query,
            "response_mode": "streaming",
            "conversation_id": conversation_id,
            "user": "Jack"
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))
        json_str = Stream_Parser(response.text).parser()
        response_data = json.loads(json_str)
        result = response_data.get('thought', 'Result not found')

        return result
