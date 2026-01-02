import streamlit as st
from discount_calc import discount
import pandas as pd
from calendar import monthrange

st.title("Credit Notes")

# Read Data
df = st.session_state["Sales Data"]
# May be modified to read data again post publishing
discount_json = st.session_state["Discount Data"] = discount.read_json_from_drive()


# Function 
def period_selection(df, selected_year, selected_month):
    filtered_df = df[(df["Year"] == selected_year) & (df["Month"] == selected_month)].copy()
    return filtered_df

def filter_discounts_for_month(discount_json, selected_year, selected_month):
    month_start = pd.Timestamp(selected_year, selected_month, 1)
    month_end = pd.Timestamp(selected_year,selected_month,monthrange(selected_year, selected_month)[1])

    applicable_discounts_json = {}

    for discount_type, records in discount_json.items():
        valid_records = []

        for r in records:
            start = pd.to_datetime(r["start_date"])
            end = pd.to_datetime(r["end_date"])

            # overlap logic
            if start <= month_end and end >= month_start:
                valid_records.append(r)

        if valid_records:
            applicable_discounts_json[discount_type] = valid_records

    return applicable_discounts_json

# Creating options for Period Selection
available_years = sorted(df["Year"].dropna().unique().astype(int))

month_map = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }

available_months = sorted(df["Month"].dropna().unique().astype(int))

st.subheader("Select Period for Discount Calculation")

col1, col2 = st.columns(2)

with col1:
    selected_year = st.selectbox(
            "Year",
            available_years,
            index=len(available_years) - 1
        )

with col2:
    selected_month = st.selectbox(
            "Month",
            available_months,
            format_func=lambda m: month_map[m]
        )

filtered_df = period_selection(df,selected_year,selected_month)
monthly_discounts = filter_discounts_for_month(discount_json, selected_year, selected_month)

if not monthly_discounts:
    st.warning("No discounts applicable for the selected month.")
    st.stop()

else:
    st.write("Monthly Discounts")
    st.success(monthly_discounts)

if filtered_df.empty:
    st.warning(
        f"No sales data found for the period"
    )
    st.stop()

else:
    st.success(
    f"Total Records: {len(filtered_df)} | "
    f"Total Quantity: {filtered_df['Quantity'].sum():,.0f}")

    df_with_discount = discount.apply_discount(filtered_df,monthly_discounts)

    st.write("Data with Discount")
    discount.render_excel_pivot(df_with_discount)

    ## Displaying Data with Aggrid
    # group_cols = ["Regional Office","Sold-to Group","Sold-to-Party Name",
    #               "Material Group","Material Description",]
    # group_df = discount.prepare_group_pivot(filtered_df,group_cols)
    # discount.render_excel_pivot(group_df)
    
    # sales_agg = discount.build_mou_summary(filtered_df,selected_year,selected_month)
    # sales_agg = discount.mou_sales_summary2(filtered_df,selected_year,selected_month)
    # discount.render_excel_pivot(sales_agg)
    # discount.render_excel_pivot(sales_agg)
    