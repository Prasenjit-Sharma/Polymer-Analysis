import streamlit as st
import pandas as pd
from reading_gsheet_data import read_data
import plotly.express as px
from sidebar import render_sidebar

# Read Sales Data
df = read_data.fetch_sales_data()


render_sidebar(df)

filtered_df = df[
    (df["Billing Date"].dt.date >= st.session_state["start_date"]) &
    (df["Billing Date"].dt.date <= st.session_state["end_date"])
]

# df = px.data.tips()
fig = px.sunburst(filtered_df, 
                path=['Plant Reg State', 'Material Group','Material Description'], 
                values='Quantity',
                title='Sales Distribution',
                )
st.plotly_chart(fig, width='stretch')

# Display Dataframe
st.dataframe(filtered_df)

# print(filtered_df.columns)
