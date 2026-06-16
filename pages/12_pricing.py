import streamlit as st
import pandas as pd
from reading_gsheet_data import read_data
import utilities

utilities.apply_common_styles("Price Finder")


with st.container(border=True):
    col1, col2, col3, col4, col5, col6, col7 = st.columns([1,1,1,1,1,1,1])
    with col1:
        price_date = st.date_input("Date", format="DD/MM/YYYY")
    with col2:
        company = st.selectbox("Company",utilities.COMPANIES)
    with col3:
        mat_family = st.selectbox("Family",utilities.FAMILY)
    with col4:
        grade = st.text_input("Grade")
    with col5:
        location = st.text_input("Location")
    with col6:
        available_price_points = utilities.PRICE_POINT_MAP.get(
            company,
            []
        )

        price_point = st.selectbox(
            "Price Point",
            available_price_points
        )
    with col7:
        if (price_point == "Plant") and (company in utilities.SPECIAL_FREIGHT_COMPANIES):
            del_location = st.text_input("Delivery Location")

    submit_button = st.button("Submit")

if submit_button:
    spreadsheet_name, freight_sheet_name = utilities.get_spreadsheet_name(company,mat_family,price_point)
    # Get Price Dataframe
    try:
        df, circular_date = read_data.read_pricing_data(spreadsheet_name, price_date)
        # Get Price from the dataframe
        price = utilities.get_price(df,grade,location)
        st.write("Date of Price Circular : ", circular_date)
        st.write("Price = ", price)
    except:
            st.write("Pricing Not Available")

    if (price_point=="Plant") and (company in utilities.SPECIAL_FREIGHT_COMPANIES):
        freight_df, circular_date= read_data.read_freight_data(freight_sheet_name,price_date)
        freight = utilities.get_freight(freight_df, del_location)
        st.write("Date of Freight Circular : ", circular_date)
        st.write("Freight = ", freight)
    

