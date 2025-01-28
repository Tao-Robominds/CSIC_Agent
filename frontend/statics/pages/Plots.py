import streamlit as st
import time
import numpy as np
import os
import sys

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from frontend.components.auth_check import check_auth

st.set_page_config(page_title="Plotting", layout="wide")

def main():
    if not check_auth():
        return
    
    st.title("Plotting")
    
    progress_bar = st.sidebar.progress(0)
    status_text = st.sidebar.empty()
    last_rows = np.random.randn(1, 1)
    chart = st.line_chart(last_rows)    

    for i in range(1, 101):
        new_rows = last_rows[-1, :] + np.random.randn(5, 1).cumsum(axis=0)
        status_text.text("%i%% Complete" % i)
        chart.add_rows(new_rows)
        progress_bar.progress(i)
        last_rows = new_rows
        time.sleep(0.05)

    progress_bar.empty()
    st.button("Re-run")

if __name__ == "__main__":
    main()