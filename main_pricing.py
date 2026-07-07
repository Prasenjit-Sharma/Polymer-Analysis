import streamlit as st
import pandas as pd
from reading_gsheet_data import read_data
from discount_calc import discount
import utilities

utilities.apply_common_styles("")

# In initial logged_in is False
if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False
if "rows" not in st.session_state:
    st.session_state.rows = []

def page_nav():
    pricing_home_page = st.Page("pages/16_home_pricing.py", title="Home", icon=":material/home:")
    product_groups_page = st.Page("pages/13_group_price.py", title="Product Group", icon=":material/ad_group:")
    product_price_page = st.Page("pages/12_pricing.py", title="Product Price", icon=":material/price_check:")
    product_compare_page = st.Page("pages/14_compare_price.py", title="Compare Price", icon=":material/balance:")
    price_circular_page = st.Page("pages/15_pricing_excel.py", title="Price Circular", icon=":material/pinboard:")

    product_groups_page_new = st.Page("pages/13_group_price_new.py", title="Product Group", icon=":material/ad_group:")

    pg = st.navigation([pricing_home_page,product_groups_page_new,product_compare_page,product_price_page,
                        price_circular_page,product_groups_page],position="top")
    
    return pg

pg = page_nav()
pg.run()