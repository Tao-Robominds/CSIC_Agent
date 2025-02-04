#!/usr/bin/env python
# -*- encoding: utf-8 -*-


from dataclasses import dataclass
from dotenv import load_dotenv
from openai import OpenAI
import os
from typing import TypedDict, List, Dict

load_dotenv()


class GPTResponse(TypedDict):
    """Response type for GPT chat"""
    status: str
    response: str
    error: str | None

@dataclass
class GPTRequest:
    """Request type for GPT chat"""
    messages: List[Dict[str, str]]
    model: str = "gpt-4o"
    temperature: float = 0
    max_tokens: int = 1000


class GPTComponent:
    """Component for interacting with GPT models"""
    
    def __init__(self, request: GPTRequest):
        """
        Initialize GPT chat component.

        Args:
            request (GPTRequest): Dataclass containing:
                messages (List[Dict[str, str]]): The conversation messages
                model (str, optional): Model name. Defaults to "gpt-4o"
                temperature (float, optional): Response randomness. Defaults to 0.7
                max_tokens (int, optional): Max response length. Defaults to 1000
        """
        self.request = request
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
    def actor(self) -> GPTResponse:
        """
        Get response from GPT synchronously.

        Returns:
            GPTResponse: Chat completion response or error information
        """
        try:            
            response = self.client.chat.completions.create(
                model=self.request.model,
                messages=self.request.messages,
                temperature=self.request.temperature,
                max_tokens=self.request.max_tokens
            )            
            response = [q.strip() for q in response.choices[0].message.content.split('\n') if q.strip()]

            return GPTResponse(
                status="success",
                response=response,
                error=None
            )
                    
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            return GPTResponse(
                status="error",
                response=None,
                error=str(e)
            ) 