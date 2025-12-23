import streamlit as st
import pandas as pd
from reading_gsheet_data import read_data

st.set_page_config(layout="wide") 

# Read Sales Data
st.session_state["Sales Data"] = df = read_data.fetch_sales_data()

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
        st.Page("pages/6_fin_credit_notes.py", title="Credit Note"),
        
    ],
}

pg = st.navigation(pages, position="top")
pg.run()

