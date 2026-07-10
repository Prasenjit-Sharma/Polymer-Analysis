import streamlit as st
import pandas as pd
from reading_gsheet_data import read_data
import utilities

utilities.apply_common_styles("Group Price Finder")

# CONFIG
# SPREADSHEET_URL = st.secrets["pricing"]["GROUP_MASTER_SHEET"]
st.session_state.group_df, st.session_state.productgroup_df, st.session_state.locationgroup_df = read_data.read_groups_data_cached()

# SESSION STATE
if "rows" not in st.session_state:
    st.session_state.rows = []
if "price_output_df" not in st.session_state:
    st.session_state.price_output_df = None
if "price_output_df" not in st.session_state:
    st.session_state.price_output_df = None
if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False


# UI
tab_price, tab_create,  tab_delete = st.tabs([":material/search_activity: Find Price",
            ":material/add_box: Create Group",":material/delete: Delete Group"])

with tab_price:
    utilities.render_find_group_price()

with tab_create:
    utilities.render_create_group()

# with tab_modify:
#     utilities.render_modify_group()

with tab_delete:
    utilities.render_delete_group()