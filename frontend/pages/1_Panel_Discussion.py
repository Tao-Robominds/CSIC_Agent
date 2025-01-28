import streamlit as st
import os
import sys
from streamlit_mic_recorder import speech_to_text

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from frontend.components.progress_bar import show_progress, cleanup_progress
from frontend.components.auth_check import check_auth
from backend.workflows.panel_discussion import CoopAgent

st.set_page_config(page_title="Business Discussion", layout="wide")

def initialize_session_state():
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []

def handle_voice_input():
    st.subheader("Voice Input")
    text = speech_to_text(
        language='en',
        use_container_width=True,
        start_prompt="Start",
        stop_prompt="Stop",
        just_once=True,
        key='stt'
    )

    if text:
        st.session_state.conversation_history.append({
            "user": text,
            "response": None
        })
        st.rerun()

def format_discussion_output(response_list):
    sections = {}
    current_section = None
    
    for item in response_list:
        if item.startswith('### '):
            current_section = item[4:]  # Remove '### '
            sections[current_section] = []
        elif current_section:
            sections[current_section].append(item)
    
    return sections

def display_conversation():
    if not st.session_state.get("authentication_status"):
        st.info("Please log in to start discussion")
        return

    for entry in st.session_state.conversation_history:
        # Display user inquiry in a container
        with st.container():
            st.markdown("---")
            st.markdown(f"**{st.session_state.username.title()}:**")
            st.info(entry['user'])

        if entry['response'] is not None:
            # First, show the discussion process
            if 'discussion_history' in entry:
                with st.expander("View Discussion Process", expanded=False):
                    for msg in entry['discussion_history']:
                        col1, col2 = st.columns([1, 4])
                        with col1:
                            st.markdown(f"**{msg['role']}:**")
                        with col2:
                            st.markdown(msg['content'])
                        st.markdown("---")
            
            # Then display team's response in a structured format
            with st.container():
                st.markdown("### Team Discussion Conclusion")
                
                # Convert the response list to structured sections
                sections = format_discussion_output(entry['response'])
                
                # Display each section with appropriate styling
                for section, content in sections.items():
                    with st.expander(section, expanded=True):
                        if section == "Key Participants":
                            for line in content:
                                st.markdown(line)
                        elif section == "Main Conclusions":
                            for item in content:
                                if not item.strip():
                                    continue
                                st.markdown(f"- {item}")
                        elif section == "Next Steps":
                            for item in content:
                                if not item.strip():
                                    continue
                                st.markdown(f"- {item}")
                        else:
                            for item in content:
                                if not item.strip():
                                    continue
                                st.markdown(item)
        else:
            # Show progress while getting response
            progress_bar, status_text = show_progress()
            coop_instance = CoopAgent(st.session_state.username, entry['user'])
            result = coop_instance.actor()
            
            # Store both the discussion history and the final response
            if isinstance(result, dict) and 'discussion_history' in result:
                entry['discussion_history'] = result['discussion_history']
                entry['response'] = result['response']
            else:
                entry['response'] = result
            
            cleanup_progress(progress_bar, status_text)
            st.rerun()

def main():
    initialize_session_state()
    
    if not check_auth():
        return
    
    st.title("Business Panel")
    
    handle_voice_input()
    display_conversation()

if __name__ == "__main__":
    main()