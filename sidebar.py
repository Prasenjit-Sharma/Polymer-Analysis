import streamlit as st
import pandas as pd

def apply_multiselect_filters(df, columns):
    filtered_df = df.copy()
    
    for col in columns:
        selected = st.multiselect(col, filtered_df[col].unique())
        if not selected:
            selected = filtered_df[col].unique()
        filtered_df = filtered_df[filtered_df[col].isin(selected)]
    
    return filtered_df

def render_sidebar(original_df=None, columns_to_filter=["Regional Office"]):

    df = original_df.copy()

    with st.sidebar:
        st.title("Filters")

        # Date Slider
        min_date = df["Billing Date"].min()
        max_date = df["Billing Date"].max()

        if pd.notna(min_date) and pd.notna(max_date):
            start_date, end_date = st.slider(
                "Billing Date range",
                min_value=min_date.date(),
                max_value=max_date.date(),
                value=(min_date.date(), max_date.date()),
                format="DD-MM-YYYY",
                key="billing_date_range"  # 🔑 important
            )
        filtered_df = df[
        (df["Billing Date"].dt.date >= start_date) &
        (df["Billing Date"].dt.date <= end_date)]

        filtered_df = apply_multiselect_filters(filtered_df, columns_to_filter)


    return filtered_df

