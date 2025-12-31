import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
from sidebar import render_sidebar

df = st.session_state["Sales Data"]

month_order = ["January", "February", "March", "April", "May", "June", 
               "July", "August", "September", "October", "November", "December"]
df['Month'] = df['Billing Date'].dt.month_name()
df['Month'] = pd.Categorical(df['Month'], categories=month_order, ordered=True)

# Hardcoded
ytd_df = df[df["Fiscal Year"]==2025]


# YTD Metrics
st.markdown("## Sales Year-To-Date")
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

col1, col2, col3 = st.columns([1,2,2], gap="small")
with col1:
    fig = px.pie(ytd_df, values='Quantity',names = 'Regional Office', title="Region Volumes")
    fig.update_traces(texttemplate='<b>%{label}</b>: <br>%{value} (%{percent})')
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width='stretch')

with col2:
    fig = px.histogram(ytd_df, x=['Regional Office'], y='Quantity',
             color='Material Group', barmode='group',text_auto=True)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
    fig.update_layout(xaxis_title="",yaxis_title="")
    st.plotly_chart(fig)

with col3:
    fig = px.sunburst(ytd_df, 
                    path=['Regional Office', 'Material Group','Material Description'], 
                    values='Quantity',
                    title='Sales Distribution',
                    )
    st.plotly_chart(fig, width='stretch')

col1, col2 = st.columns([1,2])
with col1:
    fig = px.pie(ytd_df, values='Quantity',names = 'Plant Reg State', title="Plant Volumes")
    fig.update_traces(texttemplate='<b>%{label}</b>: <br>%{value} (%{percent})')
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width='stretch')

with col2:
    fig = px.histogram(
    ytd_df.sort_values(by='Month'),
    x="Month",
    y="Quantity",
    # pattern_shape="Material Group",
    color="Plant Reg State",
    title="Monthly Quantity",
    # barmode="group", # Groups the bars side-by-side
    category_orders={"Month": month_order},
    text_auto=True
    )
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
    fig.update_layout(xaxis_title="",yaxis_title="")
    st.plotly_chart(fig, width='stretch')

# MTD Metrics
# mtd_df = ytd_df[df["Billing Date"].dt.month == 9]
mtd_df = ytd_df[df["Month"]=="December"]


st.markdown("## Sales Month-To-Date")
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


col1, col2, col3 = st.columns([1,1,2], gap="small")
with col1:
    fig = px.pie(mtd_df, values='Quantity',names = 'Regional Office', title="Region Volumes")
    fig.update_traces(texttemplate='<b>%{label}</b>: <br>%{value} (%{percent})')
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width='stretch')

with col2:
    fig = px.histogram(mtd_df, x=['Regional Office'], y='Quantity',
             color='Material Group', barmode='group',text_auto=True)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
    fig.update_layout(xaxis_title="",yaxis_title="")
    st.plotly_chart(fig)

with col3:
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
    st.plotly_chart(fig)

col1, col2 = st.columns([1,2], gap="small")


with col1:
    fig = px.pie(mtd_df, values='Quantity',names = 'Plant Reg State', title="Plant Volumes")
    fig.update_traces(texttemplate='<b>%{label}</b>: <br>%{value} (%{percent})')
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width='stretch')

with col2:
    fig = px.histogram(
    mtd_df, 
    x='Plant Reg State', 
    y='Quantity',
    color='Material Description', 
    barmode='group',
    # facet_col='Plant Reg State', # Creates a subplot for each region
    text_auto=True,
    title="Quantity by Material Description, Grouped by Plant"
    )
    # fig = px.histogram(mtd_df, x=['Regional Office'], y='Quantity',
    #         color='Material Group', barmode='group',text_auto=True)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
    fig.update_layout(xaxis_title="",yaxis_title="")
    st.plotly_chart(fig)

# Display Dataframe
# Create the pivot table
quantity_pivot = pd.pivot_table(
    mtd_df, 
    values='Quantity', 
    index=['Regional Office','Sold-to-Party Name'], # Index can include multiple columns
    columns=['Material Group', 'Material Description'], 
    aggfunc='sum', 
    fill_value=0, # Replace NaN values (where a customer didn't buy a material) with 0
    margins=True, # This adds the 'All' column (the total quantity across all materials)
    margins_name='Total Quantity' # Renames the 'All' column to 'Total Quantity'
)
st.dataframe(quantity_pivot)