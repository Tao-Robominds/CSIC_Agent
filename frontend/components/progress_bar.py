import streamlit as st
import time

def show_progress():
    """
    Display an animated progress bar with status messages.
    Returns a tuple of (progress_bar, status_text) elements.
    """
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Simulate progress
    for i in range(100):
        # Update progress bar
        progress_bar.progress(i + 1)
        
        # Update status message based on progress
        if i < 30:
            status_text.text("Thinking about your question...")
        elif i < 60:
            status_text.text("Processing information...")
        elif i < 90:
            status_text.text("Preparing response...")
        else:
            status_text.text("Finalizing...")
        
        time.sleep(0.02)

    return progress_bar, status_text

def cleanup_progress(progress_bar, status_text):
    """
    Clean up progress bar elements.
    """
    progress_bar.empty()
    status_text.empty() 