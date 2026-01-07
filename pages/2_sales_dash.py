import streamlit as st
import plotly.express as px
from sidebar import render_sidebar
import utilities
from discount_calc import discount

st.title("Sales Dashboard")

df = st.session_state["Sales Data"]
filtered_df = render_sidebar(df)

# filtered_df = df[
#     (df["Billing Date"].dt.date >= st.session_state["start_date"]) &
#     (df["Billing Date"].dt.date <= st.session_state["end_date"])
# ]

# Metrics
total_quantity_sum = filtered_df['Quantity'].sum()/1000
sum_by_group = filtered_df.groupby('Material Group')['Quantity'].sum().reset_index()
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
        fig = utilities.draw_pie(filtered_df, values='Quantity',names = 'Material Family', title="Material Family")
        st.plotly_chart(fig, width='stretch',key="ytd1")
    with col2:
        fig = utilities.draw_pie(filtered_df, values='Quantity',names = 'Material Description', title="Material Description")
        st.plotly_chart(fig, width='stretch',key="ytd2")
    with col3:
        fig = utilities.draw_sunburst(filtered_df, 
                        path=['Regional Office', 'Material Family','Material Group','Material Description'], 
                        values='Quantity',
                        title='Sales Distribution',
                        )
        st.plotly_chart(fig, width='stretch',key="ytd3")
    
# Regional
with st.container(border=True):
    col1, col2, col3 = st.columns([2,2,3], gap="small")
    with col1:
        fig = utilities.draw_pie(filtered_df, values='Quantity',names = 'Regional Office', title="Region Volumes")
        st.plotly_chart(fig, width='stretch',key="ytd4")

    with col2:
        fig = utilities.draw_histogram_bar(filtered_df, x=['Regional Office'], y='Quantity',
                color='Material Family')
        st.plotly_chart(fig,key="ytd5")

    with col3:
        fig = utilities.draw_histogram_bar(filtered_df, x=['Regional Office'], y='Quantity',
                color='Material Group')
        st.plotly_chart(fig,key="ytd6")

with st.container(border=True):
    col1, col2, col3 = st.columns([1,2, 2], gap="small")
    with col1:
        fig = utilities.draw_pie(filtered_df, values='Quantity',names = 'Plant Reg State', title="Plant Volumes")
        st.plotly_chart(fig, width='stretch', key="ytd_5")

    with col2:
        fig = utilities.draw_histogram_bar(filtered_df, x=['Plant Reg State'], y='Quantity',
                color='Material Family')
        st.plotly_chart(fig, key="ytd_6")
    
    with col3:  
        fig = utilities.draw_histogram_bar(filtered_df, x=['Plant Reg State'], y='Quantity',
                color='Material Description')
        st.plotly_chart(fig, key="ytd_7")        



with st.container(border=True):
    col1, col2 = st.columns([1,2])
    # Plant Description
    with col1:
        fig = utilities.draw_pie(filtered_df, values='Quantity',names = 'Plant Description', title="DCA Volumes")
        st.plotly_chart(fig, width='stretch',key="ytd7")

    with col2:
        fig = utilities.draw_histogram_month_quantity(filtered_df, color="Plant Description", title="Monthly Quantity")
        st.plotly_chart(fig, width='stretch',key="ytd8")

    # Material Family
    with col1:
        fig = utilities.draw_pie(filtered_df, values='Quantity',names = 'Material Family', title="Material Category")
        st.plotly_chart(fig, width='stretch',key="ytd9")

    with col2:
        fig = utilities.draw_histogram_month_quantity(filtered_df, color="Material Family", title="Monthly Quantity")
        st.plotly_chart(fig, width='stretch',key="ytd10")

    # Material Group
    with col1:
        fig = utilities.draw_pie(filtered_df, values='Quantity',names = 'Material Group', title="Material Group")
        st.plotly_chart(fig, width='stretch',key="ytd11")

    with col2:
        fig = utilities.draw_histogram_month_quantity(filtered_df, color="Material Group", title="Monthly Quantity")
        st.plotly_chart(fig, width='stretch',key="ytd12")
    
    # Material Description
    with col1:
        fig = utilities.draw_pie(filtered_df, values='Quantity',names = 'Material Description', title="Material Description")
        st.plotly_chart(fig, width='stretch',key="ytd13")

    with col2:
        fig = utilities.draw_histogram_month_quantity(filtered_df, color="Material Description", title="Monthly Quantity")
        st.plotly_chart(fig, width='stretch',key="ytd14")
    
    # Table
    col1, col2 = st.columns(2)
    
    with col1:
        is_on_sales = st.toggle("Customer Sales Table")
    with col2:
        is_on_detail = st.toggle("Detailed Sales Table")
    
    if is_on_sales:
        st.markdown("#### Customer Sales Table")
        sales_pivot = discount.prepare_group_pivot(filtered_df,
                            ["Regional Office", "Sold-to Party","Sold-to-Party Name","Sold-to Group","Material Family",
                             "Material Group","Material Description"])
        utilities.render_excel_pivot(sales_pivot,"pivot_data")
    
    if is_on_detail:
        st.markdown("#### Detailed Sales Table")
        utilities.render_excel_pivot(filtered_df,"details_data")