import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import utilities
from discount_calc import discount

st.markdown("### Sales")

df = st.session_state["Sales Data"]

month_order = ["January", "February", "March", "April", "May", "June", 
               "July", "August", "September", "October", "November", "December"]
df['Month Name'] = df['Billing Date'].dt.month_name()
df['Month Name'] = pd.Categorical(df['Month Name'], categories=month_order, ordered=True)

tab_daily, tab_month, tab_year = st.tabs(
    ["Daily", "Month-To-Date", "Year-To-Date"]
)
display_year = df.iloc[-1]['Year']
display_month = df.iloc[-1]['Month Name']
display_month_no = month_order.index(display_month)+1

with tab_year:
    # Hardcoded
    ytd_df = df[df["Fiscal Year"]==display_year]

    # Metrics
    total_quantity_sum = ytd_df['Quantity'].sum()/1000
    sum_by_group = ytd_df.groupby('Material Group')['Quantity'].sum().reset_index()
    cols = st.columns(len(sum_by_group)+1)

    with cols[0]:
        # Display Total Quantity
        st.metric(label="Total Quantity (KT)", value=f"{total_quantity_sum:,.2f}") 

    for index, row in sum_by_group.iterrows():
        with cols[index+1]:
            # Format the value nicely with commas and zero decimal places
            value_display = f"{row['Quantity']:,.0f}"
            
            st.metric(
                label=f"{row['Material Group']} (MT)", 
                value=value_display
            )

    # Overall
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([2,2,2,3], gap="small")
        with col1:
            fig = px.pie(ytd_df, values='Quantity',names = 'Regional Office', title="Region Volumes")
            fig.update_traces(texttemplate='<b>%{label}</b>: <br>%{value} (%{percent})')
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, width='stretch')

        with col2:
            fig = px.histogram(ytd_df, x=['Regional Office'], y='Quantity',
                    color='Material Family', barmode='group',text_auto=True)
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
            fig.update_layout(xaxis_title="",yaxis_title="")
            st.plotly_chart(fig)

        with col3:
            fig = px.histogram(ytd_df, x=['Regional Office'], y='Quantity',
                    color='Material Group', barmode='group',text_auto=True)
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
            fig.update_layout(xaxis_title="",yaxis_title="")
            st.plotly_chart(fig)

        with col4:
            fig = px.sunburst(ytd_df, 
                            path=['Regional Office', 'Material Group','Material Description'], 
                            values='Quantity',
                            title='Sales Distribution',
                            )
            st.plotly_chart(fig, width='stretch')

    # Regional
    with st.container(border=True):
        st.markdown("#### Filters")
        col1, col2, col3, col4 = st.columns([2,3,2,3], gap="small")
        with col1:
            select_region = st.multiselect("Region", df["Regional Office"].unique(),
                                        df["Regional Office"].unique())
            filtered_ytd_df = ytd_df[ytd_df["Regional Office"].isin(select_region)]
        with col2:
            select_dca = st.multiselect("DCA", filtered_ytd_df["Plant Description"].unique(),
                                        filtered_ytd_df["Plant Description"].unique())
            filtered_ytd_df = filtered_ytd_df[filtered_ytd_df["Plant Description"].isin(select_dca)]
        with col3:
            select_matfamily = st.multiselect("Material Family", filtered_ytd_df["Material Family"].unique(),
                                        filtered_ytd_df["Material Family"].unique())
            filtered_ytd_df = filtered_ytd_df[filtered_ytd_df["Material Family"].isin(select_matfamily)]
        with col4:
            select_matgroup = st.multiselect("Material Group", filtered_ytd_df["Material Group"].unique(),
                                        filtered_ytd_df["Material Group"].unique())
            filtered_ytd_df = filtered_ytd_df[filtered_ytd_df["Material Group"].isin(select_matgroup)]
    
    with st.container(border=True):
        col1, col2 = st.columns([1,2])
        # Plant Description
        with col1:
            fig = px.pie(filtered_ytd_df, values='Quantity',names = 'Plant Description', title="DCA Volumes")
            fig.update_traces(texttemplate='<b>%{label}</b>: <br>%{value} (%{percent})')
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, width='stretch')

        with col2:
            fig = px.histogram(
            filtered_ytd_df.sort_values(by='Month Name'),
            x="Month Name",
            y="Quantity",
            # pattern_shape="Material Group",
            color="Plant Description",
            title="Monthly Quantity",
            # barmode="group", # Groups the bars side-by-side
            category_orders={"Month Name": month_order},
            text_auto=True
            )
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
            fig.update_layout(xaxis_title="",yaxis_title="")
            st.plotly_chart(fig, width='stretch')

        # Material Family
        with col1:
            fig = px.pie(filtered_ytd_df, values='Quantity',names = 'Material Family', title="Material Category")
            fig.update_traces(texttemplate='<b>%{label}</b>: <br>%{value} (%{percent})')
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, width='stretch')

        with col2:
            fig = px.histogram(
            filtered_ytd_df.sort_values(by='Month Name'),
            x="Month Name",
            y="Quantity",
            # pattern_shape="Material Group",
            color="Material Family",
            title="Monthly Quantity",
            # barmode="group", # Groups the bars side-by-side
            category_orders={"Month Name": month_order},
            text_auto=True
            )
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
            fig.update_layout(xaxis_title="",yaxis_title="")
            st.plotly_chart(fig, width='stretch')

        # Material Group
        with col1:
            fig = px.pie(filtered_ytd_df, values='Quantity',names = 'Material Group', title="Material Group")
            fig.update_traces(texttemplate='<b>%{label}</b>: <br>%{value} (%{percent})')
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, width='stretch')

        with col2:
            fig = px.histogram(
            filtered_ytd_df.sort_values(by='Month Name'),
            x="Month Name",
            y="Quantity",
            # pattern_shape="Material Group",
            color="Material Group",
            title="Monthly Quantity",
            # barmode="group", # Groups the bars side-by-side
            category_orders={"Month Name": month_order},
            text_auto=True
            )
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
            fig.update_layout(xaxis_title="",yaxis_title="")
            st.plotly_chart(fig, width='stretch')
        
        # Material Description
        with col1:
            fig = px.pie(filtered_ytd_df, values='Quantity',names = 'Material Description', title="Material Description")
            fig.update_traces(texttemplate='<b>%{label}</b>: <br>%{value} (%{percent})')
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, width='stretch')

        with col2:
            fig = px.histogram(
            filtered_ytd_df.sort_values(by='Month Name'),
            x="Month Name",
            y="Quantity",
            # pattern_shape="Material Group",
            color="Material Description",
            title="Monthly Quantity",
            # barmode="group", # Groups the bars side-by-side
            category_orders={"Month Name": month_order},
            text_auto=True
            )
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
            fig.update_layout(xaxis_title="",yaxis_title="")
            st.plotly_chart(fig, width='stretch')
    # Sales Tables
    col1, col2 = st.columns(2)
    with col1:
        is_on_sales = st.toggle("Customer Sales Table")
    with col2:
        is_on_detail = st.toggle("Detailed Sales Table")
    
    if is_on_sales:
        st.markdown("#### Customer Sales Table")
        sales_pivot = (
            filtered_ytd_df[["Regional Office", "Sold-to Group", "Quantity"]]
            .groupby(["Regional Office","Sold-to Group"], as_index=False)
            .agg({"Quantity": "sum"}))
        utilities.render_excel_pivot(sales_pivot,"sales_ytd")

    if is_on_detail:
        st.markdown("#### Detailed Sales Table")
        utilities.render_excel_pivot(filtered_ytd_df,"details_ytd")

with tab_month:
    # MTD Metrics
    # mtd_df = ytd_df[df["Billing Date"].dt.month == 9]
    mtd_df = ytd_df[(df["Month Name"]==display_month) & (df["Year"]==display_year)]


    st.markdown(f"#### Sales Month-To-Date {display_month}-{display_year}")
    total_quantity_sum = mtd_df['Quantity'].sum()/1000
    sum_by_group = mtd_df.groupby('Material Group')['Quantity'].sum().reset_index()
    cols = st.columns(len(sum_by_group)+1)

    with cols[0]:
        # Display Total Quantity
        st.metric(label="Total Quantity (KT)", value=f"{total_quantity_sum:,.2f}") 


    for index, row in sum_by_group.iterrows():
        with cols[index+1]:
            # Format the value nicely with commas and zero decimal places
            value_display = f"{row['Quantity']:,.0f}"
            
            st.metric(
                label=f"{row['Material Group']} (MT)", 
                value=value_display
            )

    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([2,2,2,3], gap="small")
        with col1:
            fig = px.pie(mtd_df, values='Quantity',names = 'Regional Office', title="Region Volumes")
            fig.update_traces(texttemplate='<b>%{label}</b>: <br>%{value} (%{percent})')
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, width='stretch',key="mtd_1")

        with col2:
            fig = px.histogram(mtd_df, x=['Regional Office'], y='Quantity',
                    color='Material Family', barmode='group',text_auto=True)
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
            fig.update_layout(xaxis_title="",yaxis_title="")
            st.plotly_chart(fig,key="mtd_2")

        with col3:
            fig = px.histogram(mtd_df, x=['Regional Office'], y='Quantity',
                    color='Material Group', barmode='group',text_auto=True)
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
            fig.update_layout(xaxis_title="",yaxis_title="")
            st.plotly_chart(fig,key="mtd_3")
        
        with col4:
            fig = px.histogram(
            mtd_df, 
            x='Regional Office', 
            y='Quantity',
            color='Material Description', 
            barmode='group',
            # facet_col='Plant Reg State', # Creates a subplot for each region
            text_auto=True,
            title="Quantity by Material Description, Grouped by Region"
            )
            # fig = px.histogram(mtd_df, x=['Regional Office'], y='Quantity',
            #         color='Material Group', barmode='group',text_auto=True)
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
            fig.update_layout(xaxis_title="",yaxis_title="")
            st.plotly_chart(fig,key="mtd_4")


    with st.container(border=True):
        col1, col2, col3 = st.columns([1,2, 2], gap="small")
        with col1:
            fig = px.pie(mtd_df, values='Quantity',names = 'Plant Reg State', title="Plant Volumes")
            fig.update_traces(texttemplate='<b>%{label}</b>: <br>%{value} (%{percent})')
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, width='stretch', key="mtd_5")

        with col2:
            fig = px.histogram(
            mtd_df, 
            x='Plant Reg State', 
            y='Quantity',
            color='Material Family', 
            barmode='group',
            # facet_col='Plant Reg State', # Creates a subplot for each region
            text_auto=True,
            )
            # fig = px.histogram(mtd_df, x=['Regional Office'], y='Quantity',
            #         color='Material Group', barmode='group',text_auto=True)
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
            fig.update_layout(xaxis_title="",yaxis_title="")
            st.plotly_chart(fig, key="mtd_6")
        
        with col3:
            fig = px.histogram(
            mtd_df, 
            x='Plant Reg State', 
            y='Quantity',
            color='Material Description', 
            barmode='group',
            # facet_col='Plant Reg State', # Creates a subplot for each region
            text_auto=True,
            )
            # fig = px.histogram(mtd_df, x=['Regional Office'], y='Quantity',
            #         color='Material Group', barmode='group',text_auto=True)
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
            fig.update_layout(xaxis_title="",yaxis_title="")
            st.plotly_chart(fig, key="mtd_7")

    with st.container(border=True):
        st.markdown("#### Daily Upliftment")
        col1,col2 = st.columns(2)
        with col1:
            select_region = st.multiselect("Region", mtd_df["Regional Office"].unique(),
                                        mtd_df["Regional Office"].unique(), key="mtd_8")
            filtered_mtd_df = mtd_df[mtd_df["Regional Office"].isin(select_region)]
            
        with col2:
            select_dca = st.multiselect("DCA", filtered_mtd_df["Plant Description"].unique(),
                                        filtered_mtd_df["Plant Description"].unique(), key="mtd_9")
            filtered_mtd_df = filtered_mtd_df[filtered_mtd_df["Plant Description"].isin(select_dca)]
        # Daily Material Description
        fig = px.histogram(
                filtered_mtd_df.sort_values(by="Billing Date"),
                x="Billing Date",
                y="Quantity",
                color="Material Family",
                # pattern_shape="Material Description",
                text_auto=True,
                )
        # Improve axis readability
        fig.update_xaxes(dtick="D1",tickformat="%d-%b",title="Date")
        fig.update_yaxes(title="Quantity")
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
        st.plotly_chart(fig, width='stretch',key="mtd_10")

        # Daily Material Description
        fig = px.histogram(
                filtered_mtd_df.sort_values(by="Billing Date"),
                x="Billing Date",
                y="Quantity",
                color="Material Description",
                text_auto=True)
        # Improve axis readability
        fig.update_xaxes(dtick="D1",tickformat="%d-%b",title="Date")
        fig.update_yaxes(title="Quantity")
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
        st.plotly_chart(fig, width='stretch', key="mtd_11")


    with st.container(border=True):
        st.markdown("#### Sales Data")
        # Previous Month
        fiscal_order = list(range(utilities.FISCAL_START, 13)) + list(range(1, utilities.FISCAL_START))
        idx = fiscal_order.index(display_month_no)
        scheme_months = fiscal_order[:idx]
        # Get Non-Zero Data
        non_zero_pivot = discount.prepare_non_zero_avg_group_pivot(mtd_df,scheme_months,display_year,display_month_no).fillna(0)
        # MOU Data
        mou_sales_pivot = discount.prepare_mou_group_pivot(mtd_df,display_year,display_month_no).fillna(0)
        # Merge Sale, Non-Zero and MOU
        mtd_sales_pivot = discount.build_sales_mou_summary(mtd_df,mou_sales_pivot,non_zero_pivot)
        utilities.render_excel_pivot(mtd_sales_pivot,"sales_mtd")

    