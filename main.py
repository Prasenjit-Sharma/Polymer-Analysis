import streamlit as st
import pandas as pd
from reading_gsheet_data import read_data
from discount_calc import discount

st.set_page_config(layout="wide") 

# Read Sales & Discount Data
st.session_state["Sales Data"] = df = read_data.fetch_sales_data()
st.session_state["CMR Data"] = read_data.fetch_cmr_data()
st.session_state["MOU Data"] = read_data.fetch_mou_data()
st.session_state["Group Data"] = read_data.fetch_group_data()
if "cache_version" not in st.session_state:
    st.session_state.cache_version = 0
st.session_state["Discount Data"] = discount.read_json_from_drive(st.session_state.cache_version)

# Pages
pages = {
    "Sales": [
        st.Page("pages/1_home_dash.py", title="Home"),
        st.Page("pages/2_sales_dash.py", title="Dashboard"),
    ],
    "Customer": [
        st.Page("pages/3_cust_dash.py", title="Master Record"),
        st.Page("pages/4_cust_avg_price.py", title="Avg. Price"),
    ],
    "Inventory": [
        st.Page("pages/5_inventory_dash.py", title="Inventory Record"),
        
    ],
    "Finance": [
        st.Page("pages/7_fin_scheme_input.py", title="Monthly Schemes"),
        st.Page("pages/6_fin_credit_notes.py", title="Credit Note"),
        
    ],
}

pg = st.navigation(pages, position="top")
pg.run()

