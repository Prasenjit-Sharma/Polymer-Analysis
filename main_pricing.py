import streamlit as st
import pandas as pd
from reading_gsheet_data import read_data
from discount_calc import discount
import utilities

# TO DO
# 1. Groups fetch group price - 
# its limited to 1 entry for each company. like metallocene need to compare multiple grade

utilities.apply_common_styles("")

# In initial logged_in is False
if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False
if "rows" not in st.session_state:
    st.session_state.rows = []

def page_nav():
    pricing_home_page = st.Page("pages/16_home_pricing.py", title="Home", icon=":material/home:")
    product_price_page = st.Page("pages/12_pricing.py", title="Product Price", icon=":material/price_check:")
    product_compare_page = st.Page("pages/14_compare_price.py", title="Compare Price", icon=":material/balance:")
    price_circular_page = st.Page("pages/15_pricing_excel.py", title="Price Circular", icon=":material/pinboard:")
    product_groups_page = st.Page("pages/13_group_price_new.py", title="Product Group", icon=":material/ad_group:")

    mi_analysis_page = st.Page("pages/17_mi_analysis.py", title="Intelligence", icon=":material/cognition_2:")
    mi_margin_page = st.Page("pages/18_mi_margin.py", title="Margins", icon=":material/money_bag:")
    pg = st.navigation([pricing_home_page,product_groups_page,product_compare_page,product_price_page,
                        price_circular_page, mi_analysis_page, mi_margin_page],position="top")
    
    return pg

pg = page_nav()
pg.run()