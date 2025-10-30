# utils/ui_theme.py
import streamlit as st

def set_custom_page_style():
    st.markdown("""
        <style>
        .main {
            background: radial-gradient(circle at 10% 20%, #1d2033 0%, #0e101b 100%);
            color: #E0E3E7;
        }
        .stButton>button {
            background: linear-gradient(90deg, #7C4DFF, #18A0FB);
            border: none;
            color: white;
            font-weight: 600;
            border-radius: 10px;
            padding: 0.5rem 1rem;
            transition: 0.3s;
        }
        .stButton>button:hover {
            transform: scale(1.03);
            background: linear-gradient(90deg, #18A0FB, #7C4DFF);
        }
        .css-1d391kg, .css-12oz5g7 {
            background: transparent !important;
            color: #E0E3E7;
        }
        h1, h2, h3 {
            font-family: 'Segoe UI', sans-serif;
        }
        .glass-card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.4);
            border: 1px solid rgba(255,255,255,0.1);
        }
        </style>
    """, unsafe_allow_html=True)
