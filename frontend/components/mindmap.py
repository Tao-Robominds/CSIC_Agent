import graphviz
import streamlit as st
import os
from typing import Dict, Optional

class MindMap:
    def __init__(self):
        """Initialize the MindMap component."""
        self.dot = graphviz.Digraph()
        self.dot.attr(rankdir='LR')  # Left to right direction
        
        # Set graph attributes for dark theme
        self.dot.attr(bgcolor='#0E1117')
        self.dot.attr('node', 
                     shape='box', 
                     style='rounded,filled', 
                     fillcolor='#1e1e1e',
                     fontcolor='white',
                     color='#404040',
                     margin='0.3,0.2')
        
        self.dot.attr('edge',
                     color='#404040',
                     fontcolor='white')
        
        self.dot.attr(splines='ortho')
        self.dot.attr(nodesep='0.8')
        self.dot.attr(ranksep='1.2')
    
    def _wrap_text(self, text: str, width: int = 50) -> str:
        """Wrap text to specified width."""
        text = text.replace('- ', '')  # Remove bullet points
        text = ' '.join(text.split())  # Clean up whitespace
        return '\n'.join([text[i:i+width] for i in range(0, len(text), width)])

    def create_from_response(self, response: Dict) -> Optional[str]:
        """Create a mindmap from the MindSearch response."""
        try:
            # Add root node (main question)
            self.dot.node("root", self._wrap_text(response["query"]))
            
            # Get graph structure
            graph = response["graph"]
            nodes = graph["nodes"]
            
            # Process each sub-question based on the actual number of sub-questions
            for node_name, node_data in nodes.items():
                if node_name != "root":  # Skip the root node
                    # Add sub-question node
                    node_id = f"sub_q_{node_name.split('_')[-1]}"
                    self.dot.node(node_id, self._wrap_text(node_data["content"]))
                    self.dot.edge("root", node_id)
                    
                    # Add response points if they exist
                    if node_data.get("response"):
                        # Split response into individual search results
                        results = node_data["response"].split('\n')
                        for j, result in enumerate(results, 1):
                            if ']]' in result:  # Only process valid search results
                                # Extract the content after the reference
                                content = result.split(']]', 1)[1].strip()
                                point_id = f"{node_id}_{j}"
                                self.dot.node(point_id, self._wrap_text(content))
                                self.dot.edge(node_id, point_id)
            
            # Save and return the graph
            graph_path = "temp_mindmap"
            self.dot.render(graph_path, format="png", cleanup=True)
            return f"{graph_path}.png"
            
        except Exception as e:
            st.error(f"Error generating mindmap: {str(e)}")
            return None

    def display(self, response: Dict):
        """Create and display the mindmap in Streamlit."""
        mindmap_path = self.create_from_response(response)
        if mindmap_path and os.path.exists(mindmap_path):
            st.image(mindmap_path)
            os.remove(mindmap_path)