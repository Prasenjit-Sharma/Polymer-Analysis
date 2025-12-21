import streamlit as st
import pandas as pd


def render_sidebar(df=None):
    """
    Renders a common sidebar across all pages.
    Optionally accepts a DataFrame for filters.
    """

    with st.sidebar:
        st.title("Filters")

        # Date Conversion
        if df is not None and "Billing Date" in df.columns:
            df["Billing Date"] = pd.to_datetime(
                df["Billing Date"], errors="coerce"
            )

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

                # Store in session_state for all pages
                st.session_state["start_date"] = start_date
                st.session_state["end_date"] = end_date
