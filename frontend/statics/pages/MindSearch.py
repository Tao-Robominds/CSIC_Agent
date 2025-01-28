import streamlit as st
import os
import sys
import asyncio
import nest_asyncio
from streamlit_mic_recorder import speech_to_text

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from backend.components.mindsearch import MindSearchComponent, MindSearchRequest

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    # Create a proper MindSearchRequest object with an empty query
    request = MindSearchRequest(query="")
    st.session_state.mind_search_agent = MindSearchComponent(request=request)
    st.session_state.processing = False

# Apply nest_asyncio at startup
nest_asyncio.apply()

async def process_query(query: str):
    st.session_state.mind_search_agent.request.query = query
    response = st.session_state.mind_search_agent.process()
    
    if response["status"] == "success" and response["results"]:
        answer = response["results"][0]["answer"]
        references = response["results"][0]["search_results"]
    else:
        answer = "No answer found."
        references = {}
        
    return response, answer, references

def main():
    st.title("MindSearch")
    st.subheader("Voice Input")
    text = speech_to_text(
        language='en',
        use_container_width=True,
        start_prompt="Start",
        stop_prompt="Stop",
        just_once=True,
        key='stt'
    )

    # Only process if we have actual voice input
    if text and not st.session_state.processing:
        st.session_state.processing = True
        st.write("Query:", text)

        try:
            with st.spinner('Processing your query...'):
                response, answer, references = asyncio.run(process_query(text))

            if answer:
                # Create tabs for different views
                tab1, tab2, tab3 = st.tabs(["Research", "References"])
                
                with tab1:
                    st.subheader("Research Report")
                    st.markdown(f"{answer.splitlines()[0]}")
                    st.markdown("\n".join(answer.splitlines()[1:]))
                
                with tab2:
                    st.subheader("References")
                    if references:
                        # Handle references as a list of dictionaries
                        for ref in references:
                            url = ref.get('url', '')
                            name = ref.get('name', 'No title')
                            st.markdown(f"- [{name}]({url})")
                    else:
                        st.write("No references found.")

        except Exception as e:
            st.error(f"Error processing query: {str(e)}")
        finally:
            st.session_state.processing = False

if __name__ == "__main__":
    main()