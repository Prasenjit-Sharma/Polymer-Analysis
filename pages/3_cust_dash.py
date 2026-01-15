import streamlit as st
import plotly.express as px
from sidebar import render_sidebar
import utilities
from discount_calc import discount

utilities.apply_common_styles("Customer Performance")

filtered_df = st.session_state["Sales Data"]
# Last Data Available
display_year, display_fy, display_month, display_month_no = utilities.latest_data(filtered_df)
filtered_df = utilities.prepare_df_for_aggrid(filtered_df, columns_to_convert=["Fiscal Year"])

# Customer Filters
with st.container(border=True):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        select_fy = st.selectbox("Fiscal Year", filtered_df["Fiscal Year"].unique())
        # if not select_fy: select_fy = filtered_df["Regional Office"].unique()
        filtered_df = filtered_df[filtered_df["Fiscal Year"]==select_fy]    
    with col2:
        select_region = st.multiselect("Region", filtered_df["Regional Office"].unique())
        if not select_region: select_region = filtered_df["Regional Office"].unique()
        filtered_df = filtered_df[filtered_df["Regional Office"].isin(select_region)]
    with col3:
        select_custgr = st.multiselect("Customer Group", filtered_df["Sold-to Group"].unique())
        if not select_custgr: select_custgr = filtered_df["Sold-to Group"].unique()
        filtered_df = filtered_df[filtered_df["Sold-to Group"].isin(select_custgr)]
    with col4:
        select_cust = st.multiselect("Customer", filtered_df["Sold-to-Party Name"].unique())
        if not select_cust: select_cust = filtered_df["Sold-to-Party Name"].unique()
        filtered_df = filtered_df[filtered_df["Sold-to-Party Name"].isin(select_cust)]

# Sidebar
columns_to_filter = ["Billing Date","Material Family", "Material Group", "Material Description",
                     "Plant Description",]
filtered_df = render_sidebar(filtered_df, columns_to_filter)

# Tabs
with st.container(border=True):
    tab_summary, tab_total, tab_family, tab_group, tab_desc = st.tabs(
        ["Summary", "Monthly Sales", "Material Family", "Material Group", "Material Description"])


    with tab_summary:
        total_quantity_sum = filtered_df['Quantity'].sum()/1000
        # Display Total Quantity
        st.metric(label="Total Quantity (KT)", value=f"{total_quantity_sum:,.2f}") 

        col1, col2 = st.columns([1,2], gap="small")
        with col1:
            fig = utilities.draw_pie(filtered_df, values='Quantity',names = 'Material Family', title="")
            st.plotly_chart(fig, width='stretch',key="cus1")

        with col2:
            fig = utilities.draw_histogram_bar(filtered_df, x=['Material Group'], y='Quantity',
                    color='Material Description')
            st.plotly_chart(fig,key="cus2")

    with tab_total:
        fig = utilities.draw_histogram_month_quantity(df=filtered_df, title="Monthly Quantity")
        st.plotly_chart(fig, width='stretch',key="cus3")

    with tab_family:
        fig = utilities.draw_histogram_month_quantity(df=filtered_df, color="Material Family")
        st.plotly_chart(fig, width='stretch',key="cus4")

    with tab_group:
        fig = utilities.draw_histogram_month_quantity(df=filtered_df, color="Material Group")
        st.plotly_chart(fig, width='stretch',key="cus5")

    with tab_desc:
        fig = utilities.draw_histogram_month_quantity(df=filtered_df, color="Material Description")
        st.plotly_chart(fig, width='stretch',key="cus6")

# Sales Tables
with st.container(border=True):
    col1, col2,col3 = st.columns(3)
    with col1:
        is_on_mon_sales = st.toggle("Monthly Summary")
    with col2:
        is_on_daily_sales = st.toggle("Daily Summary")
    with col3:
        is_on_detail = st.toggle("Detailed Sales Table")

    if is_on_mon_sales:
        st.markdown("#### Monthly Summary")
        sales_pivot = discount.build_sales_summary(filtered_df, ["Fiscal Year", "Month Name"])
        utilities.render_excel_pivot(sales_pivot,"pivot_cus")


    if is_on_daily_sales:
        st.markdown("#### Daily Summary")
        sales_pivot = discount.build_sales_summary(filtered_df, ["Fiscal Year", "Month Name", "Billing Date"])
        utilities.render_excel_pivot(sales_pivot,"pivot_cus2")

    if is_on_detail:
        st.markdown("#### Detailed Sales Table")
        utilities.render_excel_pivot(filtered_df,"details_cus")
