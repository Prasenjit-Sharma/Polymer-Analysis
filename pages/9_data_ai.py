import utilities
import streamlit as st

utilities.apply_common_styles("Explore with AI")
import pygwalker as pyg

df = st.session_state["Sales Data"]

pyg.walk(df, env='Streamlit')

