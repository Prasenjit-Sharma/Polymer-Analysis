import streamlit as st
import pandas as pd
from reading_gsheet_data import read_data
from discount_calc import discount

st.set_page_config(layout="wide") 

def page_nav():
    # Read Sales & Discount Data
    st.session_state["Sales Data"] = df = read_data.fetch_sales_data()
    st.session_state["CMR Data"] = read_data.fetch_cmr_data()
    st.session_state["MOU Data"] = read_data.fetch_mou_data()
    st.session_state["Group Data"] = read_data.fetch_group_data()
    if "cache_version" not in st.session_state:
        st.session_state.cache_version = 0
    st.session_state["Discount Data"] = discount.read_json_from_drive(st.session_state.cache_version)

    # st.write(df.columns)

    # Pages
    pages = {
        "Sales": [
            st.Page("pages/1_home_dash.py", title="Home"),
            st.Page("pages/2_sales_dash.py", title="Dashboard"),
        ],
        "Customer": [
            st.Page("pages/3_cust_dash.py", title="Customer Performance"),
            st.Page("pages/4_cust_avg_price.py", title="Material Pricing"),
        ],
        "DCA": [
            st.Page("pages/5_dca_dash.py", title="DCA Performance"),
            
        ],
        "Finance": [
            st.Page("pages/7_fin_scheme_input.py", title="Monthly Schemes"),
            st.Page("pages/6_fin_credit_notes.py", title="Credit Note"),
            
        ],
        "Account": [
            st.Page("pages/10_logout_page.py", title="Logout", icon="🚪"),
        ],
    }

    pg = st.navigation(pages, position="top")
    pg.run()

# In initial logged_in is False
if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False

if not st.session_state["is_logged_in"]:
    with st.container():
        col1, inter_col_space, col2 = st.columns([2, 1, 2])

        with col1:
            st.image(
                "https://i1.wp.com/hrnxt.com/wp-content/uploads/2021/07/Hindustan-Petroleum.jpg?resize=580%2C239&ssl=1",
                # width=True,
                # Manually Adjust the width of the image as per requirement
            )
        with col2:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            but_login = st.button(label="Login", type="primary")

        if but_login:
            if username in st.secrets["passwords"] and password == st.secrets["passwords"][username]:
                st.session_state["is_logged_in"] = True
                st.session_state.username = username
            else:
                st.error("Invalid username or password")
else:
    page_nav()
