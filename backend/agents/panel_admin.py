#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import os
import requests
from backend.agents.utils.session_handler import SessionHandler
from backend.components.gpt_parser import GPTComponent, GPTRequest


api_key = "app-5cH3GvNV2B94L6AXupXGitwl"
url = "http://api.dify.ai.mh5.uk:8080/v1/chat-messages"
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
        self.session_id = "conversation_id"
        self.session_path = "backend/sessions"

    def _check_conversation_trigger(self, query: str) -> bool:
        """Use GPT to check if the query contains conversation triggers"""
        messages = [
            {"role": "system", "content": (
                "You are a conversation analyzer. Your task is to determine if the input contains "
                "'Hi, Donnie' or similar names. Return ONLY 'new_conv' if does, otherwise return 'same_conv'."
            )},
            {"role": "user", "content": query}
        ]

        gpt_request = GPTRequest(
            messages=messages,
            model="gpt-4o",
            temperature=0,
            max_tokens=10
        )
        
        gpt_component = GPTComponent(gpt_request)
        response = gpt_component.actor()
        
        return response["response"][0] == "new_conv"

    def perceiver(self):
        query = self.request
        return str(query)

    def actor(self):
        query = self.perceiver()
        session_handler = SessionHandler(self.session_id)

        is_new_conversation = self._check_conversation_trigger(query)
        if is_new_conversation:
            conversation_id = ""
        else:
            sessions = session_handler.load()
            conversation_id = sessions[-1]['response'] if sessions else ""

        data = {
            "inputs": {},
            "query": query,
            "response_mode": "blocking",
            "conversation_id": conversation_id,
            "user": "Jack"
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))
        response_data = response.json()
        
        if 'conversation_id' in response_data:
            session_handler.save(
                request=query,
                response=response_data['conversation_id']
            )
        
        result = response_data.get('answer', '')
        return result
