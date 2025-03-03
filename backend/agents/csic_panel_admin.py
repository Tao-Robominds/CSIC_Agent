#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import requests


api_key = "app-M1YZiWLLykgtWKkg2yjHgJ99"
url = "https://api.dify.ai/v1/chat-messages"
if not api_key:
    raise ValueError("EXTRACT_API_KEY environment variable is not set.")

headers = {
    'Authorization': 'Bearer ' + api_key,
    'Content-Type': 'application/json',
}


class PanelAdminAgent:
    def __init__(self, user_id, request):
        self.user_id = user_id
        self.request = request

    def perceiver(self):
        query = self.request
        return str(query)

    def actor(self):
        query = self.perceiver()

        data = {
            "inputs": {},
            "query": query,
            "response_mode": "blocking",
            "conversation_id": "",
            "user": self.user_id
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(data), timeout=600)
            response.raise_for_status()
            response_data = response.json()
            result = response_data.get('answer', '')
            return result
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
