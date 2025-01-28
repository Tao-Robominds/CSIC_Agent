import streamlit as st
import os
import sys
import nest_asyncio
nest_asyncio.apply()

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from frontend.components.file_upload import file_upload
from frontend.components.auth_check import check_auth

st.set_page_config(page_title="RAG", layout="wide")

def main():
    if not check_auth():
        return
    
    st.title("RAG")
    
    # Sidebar for file upload
    with st.sidebar:
        content_file = file_upload()

    # Main content area
    if content_file and os.path.exists(content_file):
        with open(content_file, "r") as f:
            content = f.read()
        st.markdown(content)
    else:
        st.info("Please upload files and process them first.")

if __name__ == "__main__":
    main()