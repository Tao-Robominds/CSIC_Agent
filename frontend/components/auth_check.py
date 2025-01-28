import streamlit as st

def check_auth():
    """
    Check authentication status and handle redirects.
    Returns True if authenticated, False otherwise.
    Also handles the redirect to Auth page if needed.
    """
    if not st.session_state.get("authentication_status"):
        # Check if we're coming from Auth page and already logged in
        if 'authentication_status' in st.session_state:
            st.rerun()  # Rerun to refresh the page with auth state
        else:
            st.warning("Please log in to use this feature.")
            st.switch_page("Donnie.py")
        return False
    return True 