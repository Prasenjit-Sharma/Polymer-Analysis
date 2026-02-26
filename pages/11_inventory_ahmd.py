import streamlit as st
import pandas as pd
import utilities
import plotly.express as px

df = st.session_state["Inventory Ahmd Data"]
# Convert to Date
df[("Product", "Date")] = pd.to_datetime(df[("Product", "Date")],dayfirst=True, format="mixed")
# Get Unique Products
products = (df.columns.get_level_values(0).unique().tolist())
products = [p for p in products if p != "Product"]

# FIlters
with st.container(border=True):
    col1, col2, col3 = st.columns([2,2.5,0.8], gap="small")
    with col1:
        # Date Slider
        min_date = df["Product"]["Date"].min()
        today = pd.Timestamp.today().normalize()
        max_sheet_date = df["Product"]["Date"].max()
        max_date = min(max_sheet_date, today)

        if pd.notna(min_date) and pd.notna(max_date):
            start_date, end_date = st.slider(
                "Date range",
                min_value=min_date.date(),
                max_value=max_date.date(),
                value=(min_date.date(), max_date.date()),
                format="DD-MM-YYYY",
                key="date_range"  # 🔑 important
            )
        df = df[
        (df["Product"]["Date"].dt.date >= start_date) &
        (df["Product"]["Date"].dt.date <= end_date)]

    with col2:
        selected_products = st.multiselect(
        "Select Products",
        options=products,
        default=products  # optional
    )
        df = df.loc[:, 
        df.columns.get_level_values(0).isin(["Product"] + selected_products)
    ]

    with col3:
        threshold = st.number_input("Low Inventory Threshold", value=100)
# Line Chart on Inventory
def draw_inventory_chart():
    # Prepare Data for Plot
    date_col = ("Product", "Date")

    # Only Opening metric
    metric_cols = [
        col for col in df.columns
        if col[1] == "Opening" and col[0] in selected_products
    ]

    plot_df = df[[date_col] + metric_cols].copy()

    # Melt to long format
    plot_df = plot_df.melt(id_vars=[date_col], value_vars=metric_cols,
                    var_name="Product", value_name="Opening Inventory")

    # Rename Date column to simple string
    plot_df.rename(columns={date_col: "Date"}, inplace=True)

    # Now plot
    fig = px.line(plot_df, x="Date", y="Opening Inventory", color="Product", markers=False)
    st.plotly_chart(fig, width="stretch")

# Metrics Table
def inventory_metric():
    
    # Low Inventory Threshold
    # threshold = 100
    total_days = len(df)

    for i in range(0, len(selected_products), 4):

        cols = st.columns(4)

        for j in range(4):

            if i + j >= len(selected_products):
                continue

            product = selected_products[i + j]

            avg_inventory = df[(product, "Opening")].mean() if (product, "Opening") in df.columns else 0
            total_in = df[(product, "In")].sum() if (product, "In") in df.columns else 0
            total_out = df[(product, "Out")].sum() if (product, "Out") in df.columns else 0

            low_days = (df[(product, "Opening")] < threshold).sum() if (product, "Opening") in df.columns else 0
            low_pct = (low_days / total_days * 100) if total_days > 0 else 0

            with cols[j]:

                with st.container(border=True):

                    st.markdown(f"### 📦 {product}")

                    st.caption("Average Inventory")
                    st.markdown(
                        f"<h2 style='margin:0; padding:0;'>{avg_inventory:,.0f}</h1>",
                        unsafe_allow_html=True
                    )

                    # In / Out indicators
                    in_col, out_col = st.columns(2)

                    with in_col:
                        st.markdown(
                            f"<span style='font-size:14px;'>In: "
                            f"<span style='color:#16a34a; font-weight:600;'>▲ {total_in:,.0f}</span></span>",
                            unsafe_allow_html=True
                        )

                    with out_col:
                        st.markdown(
                            f"<span style='font-size:14px;'>Out: "
                            f"<span style='color:#dc2626; font-weight:600;'>▼ {total_out:,.0f}</span></span>",
                            unsafe_allow_html=True
                        )

                    # st.divider()

                    risk_color = "🔴" if low_pct > 20 else "🟢"

                    st.markdown("**Low Stock Days**")
                    st.markdown(
                        f"{risk_color} {low_days} days ({low_pct:.1f}%)"
                    )

with st.container(border=True):
    tab_metric, tab_chart = st.tabs(["Metric","Chart"])

    with tab_metric:
        inventory_metric()
    with tab_chart:
        draw_inventory_chart()


    is_on_detail = st.toggle("Detailed Inventory")

    if is_on_detail:
        st.markdown("#### Detailed Inventory")
        st.table(df.style.format(precision=0))
