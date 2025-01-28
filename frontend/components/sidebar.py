import streamlit as st

def render_sidebar():
    with st.sidebar:
        st.image("frontend/statics/logo.png", width=100)
        
        # Navigation links with icons
        st.markdown("""
        <style>
        .sidebar-link {
            padding: 10px;
            border-radius: 8px;
            margin: 5px 0;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        .sidebar-link:hover {
            background-color: #2E2E2E;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Navigation items
        nav_items = {
            "🏠 Home": "Home",
            "🔍 Discover": "Discover",
            "📚 Library": "Library",
            "💡 Spaces": "Spaces"
        }
        
        for icon_label, page in nav_items.items():
            st.markdown(f"""
            <div class="sidebar-link">
                {icon_label}
            </div>
            """, unsafe_allow_html=True) 