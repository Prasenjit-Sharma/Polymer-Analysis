import streamlit as st
import pandas as pd


def render_sidebar(original_df=None):
    """
    Renders a common sidebar across all pages.
    Optionally accepts a DataFrame for filters.
    """
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

        # Regional Office
        select_region = st.multiselect("Region", filtered_df["Regional Office"].unique())
        if not select_region: select_region= filtered_df["Regional Office"].unique()
        filtered_df = filtered_df[filtered_df["Regional Office"].isin(select_region)]

        # State
        select_state = st.multiselect("State", filtered_df["Plant Reg State"].unique())
        if not select_state: select_state = filtered_df["Plant Reg State"].unique()
        filtered_df = filtered_df[filtered_df["Plant Reg State"].isin(select_state)]

        # DCA
        select_dca = st.multiselect("DCA", filtered_df["Plant Description"].unique())
        if not select_dca: select_dca = filtered_df["Plant Description"].unique()
        filtered_df = filtered_df[filtered_df["Plant Description"].isin(select_dca)]

        # Material Family
        select_matfamily = st.multiselect("Material Family", filtered_df["Material Family"].unique())
        if not select_matfamily: select_matfamily = filtered_df["Material Family"].unique()
        filtered_df = filtered_df[filtered_df["Material Family"].isin(select_matfamily)]

        # Material Group
        select_matgroup = st.multiselect("Material Group", filtered_df["Material Group"].unique())
        if not select_matgroup: select_matgroup = filtered_df["Material Group"].unique()
        filtered_df = filtered_df[filtered_df["Material Group"].isin(select_matgroup)]

        # Material Description
        select_descgroup = st.multiselect("Material Description", filtered_df["Material Description"].unique())
        if not select_descgroup: select_descgroup = filtered_df["Material Description"].unique()
        filtered_df = filtered_df[filtered_df["Material Description"].isin(select_descgroup)]

    return filtered_df

