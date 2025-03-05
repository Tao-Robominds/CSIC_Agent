#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from dataclasses import dataclass
from typing import List, Dict, Optional, Union, Any
from dotenv import load_dotenv
import os

# Import LlamaIndex components with correct import paths
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
from llama_index.core.schema import NodeWithScore

load_dotenv()

@dataclass
class LlamaIndexRequest:
    """Request type for LlamaIndex vector database retrieval"""
    query: str
    perspective: Optional[str] = None  # "project_manager", "principal_engineer", "senior_engineer"
    top_k: int = 5
    similarity_threshold: float = 0.7


class LlamaIndexResponse:
    """Response type for LlamaIndex vector database retrieval"""
    def __init__(self, 
                 status: str, 
                 nodes: Optional[List[Any]] = None, 
                 formatted_content: Optional[str] = None,
                 error: Optional[str] = None):
        self.status = status
        self.nodes = nodes
        self.formatted_content = formatted_content
        self.error = error
    
    def to_dict(self) -> Dict:
        return {
            "status": self.status,
            "formatted_content": self.formatted_content,
            "error": self.error
        }


class LlamaIndexParser:
    """Component for retrieving information from LlamaIndex vector database"""
    
    # Perspective-specific prefixes for filtering or guiding retrieval
    PERSPECTIVE_PREFIXES = {
        "project_manager": "cost budget financial investment value expenses funding allocation resources",
        "principal_engineer": "technical engineering design specifications standards methodology implementation innovation",
        "senior_engineer": "practical experience operational maintenance implementation risks execution challenges"
    }
    
    def __init__(self, request: LlamaIndexRequest):
        """
        Initialize LlamaIndex parser component.

        Args:
            request (LlamaIndexRequest): Dataclass containing:
                query (str): The search query
                perspective (Optional[str]): Perspective to filter results by
                top_k (int, optional): Number of results to return. Defaults to 5
                similarity_threshold (float, optional): Minimum similarity score. Defaults to 0.7
        """
        self.request = request
        self.index = self._initialize_index()
        
    def _initialize_index(self) -> LlamaCloudIndex:
        """Initialize connection to LlamaIndex vector database"""
        try:
            api_key = os.getenv("LLAMAINDEX_API_KEY")
            if not api_key:
                raise ValueError("LLAMAINDEX_API_KEY environment variable is not set")
                
            return LlamaCloudIndex(
                name="csic-2025",
                project_name="Default",
                organization_id="63dfc3f5-b528-471c-ac9b-f0219f94436e",
                api_key=api_key
            )
        except Exception as e:
            print(f"Error initializing LlamaIndex connection: {str(e)}")
            raise
            
    def _enhance_query_with_perspective(self, query: str, perspective: str) -> str:
        """Enhance the query with perspective-specific terms to guide retrieval"""
        if not perspective or perspective not in self.PERSPECTIVE_PREFIXES:
            return query
            
        perspective_terms = self.PERSPECTIVE_PREFIXES[perspective]
        return f"{query} {perspective_terms}"
        
    def retrieve(self) -> LlamaIndexResponse:
        """
        Retrieve information from LlamaIndex vector database.
        
        Returns:
            LlamaIndexResponse: Retrieval results or error information
        """
        try:
            # Enhance query with perspective if provided
            enhanced_query = self.request.query
            if self.request.perspective:
                enhanced_query = self._enhance_query_with_perspective(
                    self.request.query, 
                    self.request.perspective
                )
            
            # Retrieve nodes from vector database
            retriever = self.index.as_retriever(
                similarity_top_k=self.request.top_k
            )
            nodes = retriever.retrieve(enhanced_query)
            
            # Filter nodes by similarity threshold if needed
            filtered_nodes = [
                node for node in nodes 
                if not hasattr(node, 'score') or node.score >= self.request.similarity_threshold
            ]
            
            # Format the content from retrieved nodes
            formatted_content = self._format_retrieved_content(filtered_nodes)
            
            return LlamaIndexResponse(
                status="success",
                nodes=filtered_nodes,
                formatted_content=formatted_content,
                error=None
            )
                    
        except Exception as e:
            print(f"Error in LlamaIndex retrieval: {str(e)}")
            return LlamaIndexResponse(
                status="error",
                nodes=None,
                formatted_content=None,
                error=str(e)
            )
    
    def _format_retrieved_content(self, nodes: List[Any]) -> str:
        """Format the retrieved content for inclusion in agent responses"""
        if not nodes:
            return "No relevant information found in the knowledge base."
            
        formatted_sections = ["## Relevant Background Information:"]
        
        for i, node in enumerate(nodes, 1):
            # Extract text content from node - handle different node structures
            try:
                if hasattr(node, 'node') and hasattr(node.node, 'text'):
                    content = node.node.text
                elif hasattr(node, 'text'):
                    content = node.text
                else:
                    content = str(node)
                    
                score = f" (Relevance: {node.score:.2f})" if hasattr(node, 'score') else ""
                
                # Add formatted section
                formatted_sections.append(f"### Source {i}{score}")
                formatted_sections.append(content)
                formatted_sections.append("")  # Empty line for readability
            except Exception as e:
                print(f"Error formatting node {i}: {e}")
                continue
            
        return "\n".join(formatted_sections)
    
    def query(self) -> Dict:
        """
        Query the LlamaIndex vector database and return results as a dictionary.
        
        Returns:
            Dict: Query results formatted as a dictionary
        """
        response = self.retrieve()
        return response.to_dict() 