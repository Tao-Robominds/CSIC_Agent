import streamlit as st
import json
import os
import sys

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from frontend.components.auth_check import check_auth

st.set_page_config(page_title="Campaigns", layout="wide")

def main():
    if not check_auth():
        return
        
    st.title("Campaigns")
    
    # Get the campaigns structure from the JSON file
    campaigns_structure = get_campaigns_structure()

    # Create platform tabs
    platform_tabs = st.tabs(campaigns_structure.keys())

    for platform_idx, (platform, campaigns) in enumerate(campaigns_structure.items()):
        with platform_tabs[platform_idx]:
            st.header(platform)
            
            # Create campaign tabs for each platform
            campaign_tabs = st.tabs(campaigns.keys())
            
            for campaign_idx, (campaign_name, campaign_data) in enumerate(campaigns.items()):
                with campaign_tabs[campaign_idx]:
                    display_campaign_content(campaign_name, campaign_data)

def get_campaigns_structure():
    """Load campaign structure from JSON file"""
    try:
        with open("frontend/statics/compaigns.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Campaigns configuration file not found!")
        return {}
    except json.JSONDecodeError:
        st.error("Invalid JSON format in campaigns configuration!")
        return {}

def display_campaign_content(campaign_name, campaign_data):
    """Display campaign content in an organized layout"""
    # Campaign header with status
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(campaign_name)
    with col2:
        status = campaign_data['status'].upper()
        if status == "ACTIVE":
            st.success(f"**Status:** {status}")
        elif status == "PENDING":
            st.warning(f"**Status:** {status}")
        elif status == "COMPLETED":
            st.info(f"**Status:** {status}")
        elif status == "CANCELLED":
            st.error(f"**Status:** {status}")
        else:
            st.markdown(f"**Status:** {status}")
    
    # Timeline
    st.markdown(f"**Timeline:** {campaign_data['timeline']}")
    
    # Objectives and Metrics in columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Objectives")
        for obj in campaign_data['objectives']:
            st.markdown(f"- {obj}")
    
    with col2:
        st.markdown("### Key Metrics")
        for metric in campaign_data['metrics']:
            st.markdown(f"- {metric}")

if __name__ == "__main__":
    main()