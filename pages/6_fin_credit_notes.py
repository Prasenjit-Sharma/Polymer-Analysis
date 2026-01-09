import streamlit as st
from discount_calc import discount
import pandas as pd
from calendar import monthrange
import utilities

utilities.apply_common_styles("Credit Notes")

# Read Data
df = st.session_state["Sales Data"]
# May be modified to read data again post publishing
discount_json = st.session_state["Discount Data"] = discount.read_json_from_drive(st.session_state.cache_version)

selected_year, selected_month, filtered_df = utilities.period_selection(df)
monthly_discounts = discount.filter_discounts_for_month(discount_json, selected_year, selected_month)

if not monthly_discounts:
    st.warning("No discounts applicable for the selected month.")
    st.stop()

if filtered_df.empty:
    st.warning(f"No sales data found for the period")
    st.stop()
else:
    df_with_discount = discount.apply_discount(filtered_df,monthly_discounts, selected_year, selected_month)

    discount_pivot = (
        df_with_discount[["Regional Office", "Sold-to Party","Sold-to-Party Name", "Sold-to Group", "Quantity", "Month Credit Note"]]
        .groupby(["Regional Office", "Sold-to Party","Sold-to-Party Name","Sold-to Group"], as_index=False)
        .agg({"Quantity": "sum","Month Credit Note": "sum"}))
    st.markdown("#### Discount Summary")
    utilities.render_excel_pivot(discount_pivot,"discount_summary")

    # Create a toggle widget
    is_on = st.toggle("Detailed Table")

    # Conditionally display content based on the toggle state
    if is_on:
        st.markdown("#### Discount Details")
        utilities.render_excel_pivot(df_with_discount,"discount_detail")

    
