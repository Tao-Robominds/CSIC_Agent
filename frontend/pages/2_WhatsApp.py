import streamlit as st
import os
import sys
import json
import time
from datetime import datetime

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from backend.components.whatsapp_sender import WhatsAppSenderRequest, WhatsAppSender
from frontend.components.auth_check import check_auth

st.set_page_config(page_title="WhatsApp Chat", layout="wide")

def load_messages():
    """Load messages from storage"""
    filepath = "storage/messages/received_messages.json"
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            messages = json.load(f)
            return messages[-10:] if len(messages) > 10 else messages
    return []

def main():
    if not check_auth():
        return
    
    st.title("WhatsApp Chat")

    # Initialize session state
    if 'last_message_count' not in st.session_state:
        st.session_state.last_message_count = 0
    if 'sent_messages' not in st.session_state:
        st.session_state.sent_messages = []

    # Message input at the top
    message = st.text_input("Type a message", key="message_input")
    
    if st.button("Send", type="primary"):
        if message:
            try:
                request = WhatsAppSenderRequest(
                    message=message,
                    recipient_number="447948757785"
                )
                sender = WhatsAppSender(request)
                response = sender.send_message()
                
                if response["status"] == "success":
                    st.session_state.sent_messages.append({
                        "message": message,
                        "timestamp": datetime.now().strftime("%H:%M")
                    })
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")

    # Chat display area
    chat_container = st.container()
    
    # Display messages
    with chat_container:
        # Get received messages
        received_messages = load_messages()
        
        # Display messages
        for msg in received_messages:
            timestamp = datetime.fromisoformat(msg["timestamp"]).strftime("%H:%M")
            st.write(f"Received ({timestamp}): {msg['message']}")
        
        # Display sent messages
        for msg in st.session_state.sent_messages:
            st.write(f"You ({msg['timestamp']}): {msg['message']}")

    # Auto-refresh check
    if len(received_messages) != st.session_state.last_message_count:
        st.session_state.last_message_count = len(received_messages)
        time.sleep(2)
        st.rerun()

if __name__ == "__main__":
    main()
