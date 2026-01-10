import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import utilities
from discount_calc import discount



df = st.session_state["Sales Data"]
last_date = df['Billing Date'].drop_duplicates().nlargest(1)
formatted_date = last_date.iloc[0].strftime('%d-%b-%Y')
utilities.apply_common_styles(f"Sales Summary - {formatted_date}")

# Creating Month Order
month_order = utilities.month_order
df['Month Name'] = pd.Categorical(df['Month Name'], categories=month_order, ordered=True)

tab_daily, tab_month, tab_year = st.tabs(["Daily", "Month-To-Date", "Year-To-Date"])

# Last Data Available
display_year, display_fy, display_month, display_month_no = utilities.latest_data(df)

with tab_year:
    yr_tab_summary, yr_tab_region, yr_tab_state, yr_tab_day = st.tabs(["Summary", "Regional Office", "State","Day Wise Sales"])
    ytd_df = df[df["Fiscal Year"]==display_fy]

    with st.container(border=True):
        with yr_tab_summary:
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

            # Overall Charts
            with st.container(border=True):
                col1, col2, col3= st.columns(3, gap="small")
                with col1:
                    fig = utilities.draw_pie(ytd_df, values='Quantity',names = 'Material Family', title="Material Family")
                    st.plotly_chart(fig, width='stretch',key="ytd1")
                with col2:
                    fig = utilities.draw_pie(ytd_df, values='Quantity',names = 'Material Description', title="Material Description")
                    st.plotly_chart(fig, width='stretch',key="ytd2")
                with col3:
                    fig = utilities.draw_sunburst(ytd_df, 
                                    path=['Regional Office', 'Material Family','Material Group','Material Description'], 
                                    values='Quantity',
                                    title='Sales Distribution',
                                    )
                    st.plotly_chart(fig, width='stretch',key="ytd3")
        
        with yr_tab_region:
            with st.container(border=True):
                # Regional
                col1, col2, col3 = st.columns([2,2,3], gap="small")
                with col1:
                    fig = utilities.draw_pie(ytd_df, values='Quantity',names = 'Regional Office', title="Region Volumes")
                    st.plotly_chart(fig, width='stretch',key="ytd4")

                with col2:
                    fig = utilities.draw_histogram_bar(ytd_df, x=['Regional Office'], y='Quantity',
                            color='Material Family')
                    st.plotly_chart(fig,key="ytd5")

                with col3:
                    fig = utilities.draw_histogram_bar(ytd_df, x=['Regional Office'], y='Quantity',
                            color='Material Group')
                    st.plotly_chart(fig,key="ytd6")

        with yr_tab_state:
            with st.container(border=True):
                col1, col2, col3 = st.columns([1,2, 2], gap="small")
                with col1:
                    fig = utilities.draw_pie(ytd_df, values='Quantity',names = 'Plant Reg State', title="Plant Volumes")
                    st.plotly_chart(fig, width='stretch', key="ytd_5")

                with col2:
                    fig = utilities.draw_histogram_bar(ytd_df, x=['Plant Reg State'], y='Quantity',
                            color='Material Family')
                    st.plotly_chart(fig, key="ytd_6")
                
                with col3:  
                    fig = utilities.draw_histogram_bar(ytd_df, x=['Plant Reg State'], y='Quantity',
                            color='Material Description')
                    st.plotly_chart(fig, key="ytd_7")        

        with yr_tab_day:
            col1, col2, col3, col4 = st.columns([2,3,2,3], gap="small")
            with col1:
                select_region = st.multiselect("Region", df["Regional Office"].unique(),
                                            df["Regional Office"].unique())
                filtered_ytd_df = ytd_df[ytd_df["Regional Office"].isin(select_region)]
            with col2:
                select_dca = st.multiselect("DCA", filtered_ytd_df["Plant Description"].unique())
                if not select_dca: select_dca = filtered_ytd_df["Plant Description"].unique()
                filtered_ytd_df = filtered_ytd_df[filtered_ytd_df["Plant Description"].isin(select_dca)]
            with col3:
                select_matfamily = st.multiselect("Material Family", filtered_ytd_df["Material Family"].unique())
                if not select_matfamily: select_matfamily = filtered_ytd_df["Material Family"].unique()
                filtered_ytd_df = filtered_ytd_df[filtered_ytd_df["Material Family"].isin(select_matfamily)]
            with col4:
                select_matgroup = st.multiselect("Material Group", filtered_ytd_df["Material Group"].unique())
                if not select_matgroup: select_matgroup = filtered_ytd_df["Material Group"].unique()
                filtered_ytd_df = filtered_ytd_df[filtered_ytd_df["Material Group"].isin(select_matgroup)]
        
            with st.container(border=True):
                option = st.radio("Chart Options:",("DCA", "Material Family", 
                                        "Material Group","Material Description"),
                                        horizontal=True, key="radio_yr")
                col1, col2 = st.columns([1,2])

                if option == "DCA":
                    # Plant Description
                    with col1:
                        fig = utilities.draw_pie(filtered_ytd_df, values='Quantity',names = 'Plant Description', title="DCA Volumes")
                        st.plotly_chart(fig, width='stretch',key="ytd7")

                    with col2:
                        fig = utilities.draw_histogram_month_quantity(filtered_ytd_df, color="Plant Description", title="Monthly Quantity")
                        st.plotly_chart(fig, width='stretch',key="ytd8")

                # Material Family
                if option == "Material Family":
                    with col1:
                        fig = utilities.draw_pie(filtered_ytd_df, values='Quantity',names = 'Material Family', title="Material Category")
                        st.plotly_chart(fig, width='stretch',key="ytd9")

                    with col2:
                        fig = utilities.draw_histogram_month_quantity(filtered_ytd_df, color="Material Family", title="Monthly Quantity")
                        st.plotly_chart(fig, width='stretch',key="ytd10")

                # Material Group
                if option == "Material Group":
                    with col1:
                        fig = utilities.draw_pie(filtered_ytd_df, values='Quantity',names = 'Material Group', title="Material Group")
                        st.plotly_chart(fig, width='stretch',key="ytd11")

                    with col2:
                        fig = utilities.draw_histogram_month_quantity(filtered_ytd_df, color="Material Group", title="Monthly Quantity")
                        st.plotly_chart(fig, width='stretch',key="ytd12")
                
                # Material Description
                if option == "Material Description":
                    with col1:
                        fig = utilities.draw_pie(filtered_ytd_df, values='Quantity',names = 'Material Description', title="Material Description")
                        st.plotly_chart(fig, width='stretch',key="ytd13")

                    with col2:
                        fig = utilities.draw_histogram_month_quantity(filtered_ytd_df, color="Material Description", title="Monthly Quantity")
                        st.plotly_chart(fig, width='stretch',key="ytd14")
    
        with st.container(border=True):
            # Sales Tables
            col1, col2 = st.columns(2)
            with col1:
                is_on_sales = st.toggle("Customer Sales Table")
            with col2:
                is_on_detail = st.toggle("Detailed Sales Table")
            
            if is_on_sales:
                st.markdown("#### Customer Sales Table")
                sales_pivot = discount.prepare_group_pivot(filtered_ytd_df,
                                    ["Regional Office", "Sold-to Group"])
                utilities.render_excel_pivot(sales_pivot,"sales_ytd")

            if is_on_detail:
                st.markdown("#### Detailed Sales Table")
                utilities.render_excel_pivot(filtered_ytd_df,"details_ytd")

with tab_month:
    mon_tab_summary, mon_tab_region, mon_tab_state, mon_tab_day = st.tabs(["Summary", 
                                                    "Regional Office", "State","Day Wise Sales"])
    with st.container(border=True):
        with mon_tab_summary:
            # MTD Metrics
            mtd_df = df[(df["Month Name"]==display_month) & (df["Year"]==display_year)]


            st.markdown(f"#### Sales Month-To-Date {display_month}-{display_year}")
            total_quantity_sum = mtd_df['Quantity'].sum()/1000
            sum_by_group = mtd_df.groupby('Material Group')['Quantity'].sum().reset_index()
            cols = st.columns(len(sum_by_group)+1)

            # Metrics
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

            # Overall Charts
            with st.container(border=True):
                col1, col2, col3= st.columns(3, gap="small")
                with col1:
                    fig = utilities.draw_pie(mtd_df, values='Quantity',names = 'Material Family', title="Material Family")
                    st.plotly_chart(fig, width='stretch',key="mtd1")
                with col2:
                    fig = utilities.draw_pie(mtd_df, values='Quantity',names = 'Material Description', title="Material Description")
                    st.plotly_chart(fig, width='stretch',key="mtd2")
                with col3:
                    fig = utilities.draw_sunburst(mtd_df, 
                                    path=['Regional Office', 'Material Family','Material Group','Material Description'], 
                                    values='Quantity',
                                    title='Sales Distribution',
                                    )
                    st.plotly_chart(fig, width='stretch',key="mtd3")

        # Regional Office
        with mon_tab_region:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([2,2,2,3], gap="small")
                with col1:
                    fig = utilities.draw_pie(mtd_df, values='Quantity',names = 'Regional Office', title="Region Volumes")
                    st.plotly_chart(fig, width='stretch',key="mtd_1")

                with col2:
                    fig = utilities.draw_histogram_bar(mtd_df, x=['Regional Office'], y='Quantity',
                            color='Material Family')
                    st.plotly_chart(fig,key="mtd_2")

                with col3:
                    fig = utilities.draw_histogram_bar(mtd_df, x=['Regional Office'], y='Quantity',
                            color='Material Group')
                    st.plotly_chart(fig,key="mtd_3")
                
                with col4:
                    fig = utilities.draw_histogram_bar(mtd_df, x=['Regional Office'], y='Quantity',
                            color='Material Description')
                    st.plotly_chart(fig,key="mtd_4")

        # State
        with mon_tab_state:
            with st.container(border=True):
                col1, col2, col3 = st.columns([1,2, 2], gap="small")
                with col1:
                    fig = utilities.draw_pie(mtd_df, values='Quantity',names = 'Plant Reg State', title="Plant Volumes")
                    st.plotly_chart(fig, width='stretch', key="mtd_5")

                with col2:
                    fig = utilities.draw_histogram_bar(mtd_df, x=['Plant Reg State'], y='Quantity',
                            color='Material Family')
                    st.plotly_chart(fig, key="mtd_6")
                
                with col3:  
                    fig = utilities.draw_histogram_bar(mtd_df, x=['Plant Reg State'], y='Quantity',
                            color='Material Description')
                    st.plotly_chart(fig, key="mtd_7")

        # Daily
        with mon_tab_day:
            with st.container(border=True):
                col1,col2,col3 = st.columns(3)
                with col1:
                    select_region = st.multiselect("Region", mtd_df["Regional Office"].unique(),
                                                mtd_df["Regional Office"].unique(), key="mtd_8")
                    filtered_mtd_df = mtd_df[mtd_df["Regional Office"].isin(select_region)]
                with col2:
                    select_state = st.multiselect("State", mtd_df["Plant Reg State"].unique(), key="mtd_8a")
                    if not select_state: select_state = mtd_df["Plant Reg State"].unique()
                    filtered_mtd_df = mtd_df[mtd_df["Plant Reg State"].isin(select_state)]
                with col3:
                    select_dca = st.multiselect("DCA", filtered_mtd_df["Plant Description"].unique(), key="mtd_9")
                    if not select_dca: select_dca = filtered_mtd_df["Plant Description"].unique()
                    filtered_mtd_df = filtered_mtd_df[filtered_mtd_df["Plant Description"].isin(select_dca)]
                
                option = st.radio("Chart Options:",("DCA", "Material Family", 
                                        "Material Group","Material Description"),
                                        horizontal=True, key="radio_mon")
                # DCA
                if option == "DCA":
                    fig = utilities.draw_histogram_bar(filtered_mtd_df, x=['Billing Date'], y='Quantity',
                                color='Plant Description')
                    # Improve axis readability
                    fig.update_xaxes(dtick="D1",tickformat="%d-%b",title="Date")
                    fig.update_yaxes(title="Quantity")
                    st.plotly_chart(fig, width='stretch',key="mtd_10a")

                # Material Family
                if option == "Material Family":
                    fig = utilities.draw_histogram_bar(filtered_mtd_df, x=['Billing Date'], y='Quantity',
                                color='Material Family')
                    # Improve axis readability
                    fig.update_xaxes(dtick="D1",tickformat="%d-%b",title="Date")
                    fig.update_yaxes(title="Quantity")
                    st.plotly_chart(fig, width='stretch',key="mtd_10b")

                # Material Group
                if option == "Material Group":
                    fig = utilities.draw_histogram_bar(filtered_mtd_df, x=['Billing Date'], y='Quantity',
                                color='Material Group')
                    # Improve axis readability
                    fig.update_xaxes(dtick="D1",tickformat="%d-%b",title="Date")
                    fig.update_yaxes(title="Quantity")
                    st.plotly_chart(fig, width='stretch',key="mtd_10")

                # Material Description
                if option == "Material Description":
                    fig = utilities.draw_histogram_bar(filtered_mtd_df, x=['Billing Date'], y='Quantity',
                                color='Material Description')
                    # Improve axis readability
                    fig.update_xaxes(dtick="D1",tickformat="%d-%b",title="Date")
                    fig.update_yaxes(title="Quantity")
                    st.plotly_chart(fig, width='stretch', key="mtd_11")

        # Sales Tables
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                is_on_sales = st.toggle("Customer Sales Table", key="mtd_pivot")
            with col2:
                is_on_detail = st.toggle("Detailed Sales Table", key="mtd_detail")
            
            if is_on_sales:
                st.markdown("#### Customer Sales Table")
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
                utilities.render_excel_pivot(mtd_sales_pivot,"mtd15")

            if is_on_detail:
                st.markdown("#### Detailed Sales Table")
                utilities.render_excel_pivot(filtered_mtd_df,"mtd16")

with tab_daily:
    option_day = st.radio("Select Working Days",["Last Day","Last 2 Days","Last 3 Days","Last 7 Days"], 
                          horizontal=True)
    if option_day == "Last Day":
        last_dates = df['Billing Date'].drop_duplicates().nlargest(1)
    elif option_day == "Last 2 Days":
        last_dates = df['Billing Date'].drop_duplicates().nlargest(2)
    elif option_day == "Last 3 Days":
        last_dates = df['Billing Date'].drop_duplicates().nlargest(3)
    elif option_day == "Last 7 Days":
        last_dates = df['Billing Date'].drop_duplicates().nlargest(7)
    
    day_df = df[df['Billing Date'].isin(last_dates)]

    day_tab_summary, day_tab_region, day_tab_state, day_tab_day = st.tabs(["Summary", 
                                            "Regional Office", "State","Day Wise Sales"])
    
    with day_tab_summary:
        total_quantity_sum_day = day_df['Quantity'].sum()/1000 # type: ignore
        sum_by_group_day = day_df.groupby('Material Group')['Quantity'].sum().reset_index()
        cols_day = st.columns(len(sum_by_group_day)+1)

        # Metrics
        with cols_day[0]:
            # Display Total Quantity
            st.metric(label="Total Quantity (KT)", value=f"{total_quantity_sum_day:,.2f}") 

        for index, row in sum_by_group_day.iterrows():
            with cols_day[index+1]:
                # Format the value nicely with commas and zero decimal places
                value_display = f"{row['Quantity']:,.0f}"
                
                st.metric(
                    label=f"{row['Material Group']} (MT)", 
                    value=value_display
                )
        
        # Overall Charts
        with st.container(border=True):
            col1, col2, col3= st.columns(3, gap="small")
            with col1:
                fig = utilities.draw_pie(day_df, values='Quantity',names = 'Material Family', title="Material Family")
                st.plotly_chart(fig, width='stretch',key="day1")
            with col2:
                fig = utilities.draw_pie(day_df, values='Quantity',names = 'Material Description', title="Material Description")
                st.plotly_chart(fig, width='stretch',key="day2")
            with col3:
                fig = utilities.draw_sunburst(day_df, 
                                path=['Regional Office', 'Material Family','Material Group','Material Description'], 
                                values='Quantity',
                                title='Sales Distribution',
                                )
                st.plotly_chart(fig, width='stretch',key="day3")

    with day_tab_region:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2,2,2,3], gap="small")
            with col1:
                fig = utilities.draw_pie(day_df, values='Quantity',names = 'Regional Office', title="Region Volumes")
                st.plotly_chart(fig, width='stretch',key="day4")

            with col2:
                fig = utilities.draw_histogram_bar(day_df, x=['Regional Office'], y='Quantity',
                        color='Material Family')
                st.plotly_chart(fig,key="day5")

            with col3:
                fig = utilities.draw_histogram_bar(day_df, x=['Regional Office'], y='Quantity',
                        color='Material Group')
                st.plotly_chart(fig,key="day6")
            
            with col4:
                fig = utilities.draw_histogram_bar(day_df, x=['Regional Office'], y='Quantity',
                        color='Material Description')
                st.plotly_chart(fig,key="day7")   

    with day_tab_state:
        with st.container(border=True):
            col1, col2, col3 = st.columns([2,2, 3], gap="small")
            with col1:
                fig = utilities.draw_pie(day_df, values='Quantity',names = 'Plant Reg State', title="Plant Volumes")
                st.plotly_chart(fig, width='stretch', key="day8")

            with col2:
                fig = utilities.draw_histogram_bar(day_df, x=['Plant Reg State'], y='Quantity',
                        color='Material Family')
                st.plotly_chart(fig, key="day9")
            
            with col3:  
                fig = utilities.draw_histogram_bar(day_df, x=['Plant Reg State'], y='Quantity',
                        color='Material Description')
                st.plotly_chart(fig, key="day10")

    with day_tab_day:
        with st.container(border=True):
            st.markdown("#### Daily Upliftment")
            col1,col2 = st.columns(2)
            with col1:
                select_region = st.multiselect("Region", day_df["Regional Office"].unique(), # type: ignore
                                            day_df["Regional Office"].unique(), key="day11") # type: ignore
                filtered_day_df = day_df[day_df["Regional Office"].isin(select_region)] # type: ignore
                
            with col2:
                select_dca = st.multiselect("DCA", filtered_day_df["Plant Description"].unique(), key="day12") # type: ignore
                if not select_dca: select_dca= filtered_day_df["Plant Description"].unique() # type: ignore
                filtered_day_df = filtered_day_df[filtered_day_df["Plant Description"].isin(select_dca)] # type: ignore
            
            option = st.radio("Chart Options:",("Material Family", 
                                        "Material Group","Material Description"),
                                        horizontal=True, key="radio_day")
            
            # Daily Material Family
            if option == "Material Family":
                fig = utilities.draw_histogram_bar(filtered_day_df, x=['Billing Date'], y='Quantity',
                            color='Material Family')
                # Improve axis readability
                fig.update_xaxes(dtick="D1",tickformat="%d-%b",title="Date")
                fig.update_yaxes(title="Quantity")
                st.plotly_chart(fig, width='stretch',key="day13")

            # Daily Material Group
            if option == "Material Group":
                fig = utilities.draw_histogram_bar(filtered_day_df, x=['Billing Date'], y='Quantity',
                            color='Material Group')
                # Improve axis readability
                fig.update_xaxes(dtick="D1",tickformat="%d-%b",title="Date")
                fig.update_yaxes(title="Quantity")
                st.plotly_chart(fig, width='stretch',key="day13")

            # Daily Material Description
            if option == "Material Description":
                fig = utilities.draw_histogram_bar(filtered_day_df, x=['Billing Date'], y='Quantity',
                            color='Material Description')
                # Improve axis readability
                fig.update_xaxes(dtick="D1",tickformat="%d-%b",title="Date")
                fig.update_yaxes(title="Quantity")
                st.plotly_chart(fig, width='stretch', key="day14")

    with st.container(border=True):
        # Sales Tables
        col1, col2 = st.columns(2)
        with col1:
            is_on_sales = st.toggle("Customer Sales Table", key="day_pivot")
        with col2:
            is_on_detail = st.toggle("Detailed Sales Table", key="day_detail")
        
        if is_on_sales:
            st.markdown("#### Customer Sales Table")
            # Previous Month
            fiscal_order = list(range(utilities.FISCAL_START, 13)) + list(range(1, utilities.FISCAL_START))
            idx = fiscal_order.index(display_month_no)
            scheme_months = fiscal_order[:idx]
            # Get Non-Zero Data
            non_zero_pivot_day = discount.prepare_non_zero_avg_group_pivot(day_df,scheme_months,display_year,display_month_no).fillna(0)
            # MOU Data
            mou_sales_pivot_day = discount.prepare_mou_group_pivot(day_df,display_year,display_month_no).fillna(0)
            # Merge Sale, Non-Zero and MOU
            mtd_sales_pivot = discount.build_sales_mou_summary(day_df,mou_sales_pivot_day,non_zero_pivot_day)
            # day_sales_pivot = discount.build_sales_summary(day_df)
            utilities.render_excel_pivot(mtd_sales_pivot,"day15")

        if is_on_detail:
            st.markdown("#### Detailed Sales Table")
            utilities.render_excel_pivot(filtered_day_df,"day16")

