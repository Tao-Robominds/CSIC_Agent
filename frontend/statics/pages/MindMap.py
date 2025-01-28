import streamlit as st
import os
import sys
import json
from typing import Dict, Optional

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from frontend.components.mindmap import MindMap
from frontend.components.auth_check import check_auth

st.set_page_config(page_title="Mind Map", layout="wide")

def load_mindsearch_data() -> Optional[Dict]:
    """Load data from mindsearch.json file."""
    try:
        json_path = os.path.join("frontend", "statics", "mindsearch.json")
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("mindsearch.json file not found!")
        return None
    except json.JSONDecodeError:
        st.error("Invalid JSON format in mindsearch.json!")
        return None

def main():
    if not check_auth():
        return
        
    st.title("Mind Map")
    
    # Add a refresh button
    if st.button("Refresh Mind Map"):
        st.rerun()
    
    # Create tabs for different views
    tab1, tab2 = st.tabs(["Mind Map", "Raw Data"])
    
    # Load the mindsearch data
    data = load_mindsearch_data()
    
    if data:
        with tab1:
            st.subheader("Mind Map Visualization")
            # Create and display the mindmap
            mindmap = MindMap()
            mindmap.display(data)
            
        with tab2:
            st.subheader("Raw JSON Data")
            # Display the raw JSON data in a formatted way
            st.json(data)
            
            # Display the answer text separately for better readability
            if "answer" in data:
                st.subheader("Formatted Answer")
                st.markdown(data["answer"])
                
            # Display references if available
            if "graph" in data and "references" in data["graph"]:
                st.subheader("References")
                for ref_id, url in data["graph"]["references"].items():
                    st.markdown(f"{ref_id}: [{url}]({url})")
    else:
        st.warning("No data available to display. Please check the mindsearch.json file.")

if __name__ == "__main__":
    main() 