import streamlit as st
import pandas as pd
from reading_gsheet_data import read_data
from discount_calc import discount
import utilities

utilities.apply_common_styles("")

# In initial logged_in is False
if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False

def page_nav():
    product_groups_page = st.Page("pages/13_group_price.py", title="Product Group", icon=":material/percent_discount:")
    product_price_page = st.Page("pages/12_pricing.py", title="Product Price", icon=":material/percent_discount:")

    pg = st.navigation([product_groups_page,product_price_page],position="top")

    return pg

pg = page_nav()
pg.run()