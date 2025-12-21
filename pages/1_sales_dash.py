import streamlit as st
import plotly.express as px
from sidebar import render_sidebar

st.title("Sales Dashboard")

df = st.session_state["Sales Data"]
render_sidebar(df)

filtered_df = df[
    (df["Billing Date"].dt.date >= st.session_state["start_date"]) &
    (df["Billing Date"].dt.date <= st.session_state["end_date"])
]


fig = px.sunburst(filtered_df, 
                path=['Plant Reg State', 'Material Group','Material Description'], 
                values='Quantity',
                title='Sales Distribution',
                )
st.plotly_chart(fig, width='stretch')

# Display Dataframe
st.dataframe(filtered_df)