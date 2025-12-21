import streamlit as st
import pandas as pd
from reading_gsheet_data import read_data


# Read Sales Data
st.session_state["Sales Data"] = df = read_data.fetch_sales_data()

# Pages
pages = {
    "Dashboard": [
        st.Page("pages/1_sales_dash.py", title="Sales"),

    ],
    "Others": [
        st.Page("pages/2_cust_dash.py", title="Customer"),
    ],
}

pg = st.navigation(pages, position="top")
pg.run()

