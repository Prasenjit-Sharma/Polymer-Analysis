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

# Metrics
total_quantity_sum = filtered_df['Quantity'].sum()/1000
sum_by_group = filtered_df.groupby('Material Group')['Quantity'].sum().reset_index()
cols = st.columns(len(sum_by_group)+1)

with cols[0]:
    # Display Total Quantity
    st.metric(label="Total Quantity", value=f"{total_quantity_sum:,.2f} KT") 


for index, row in sum_by_group.iterrows():
    with cols[index+1]:
        # Format the value nicely with commas and zero decimal places
        value_display = f"{row['Quantity']:,.0f}"
        
        st.metric(
            label=f"{row['Material Group']}", 
            value=value_display
        )
# Column for Charts
col1, col2,col3 = st.columns(3)
with col1:
    fig = px.pie(filtered_df, values='Quantity',names = 'Regional Office', title="Region Volumes")
    fig.update_traces(texttemplate='<b>%{label}</b>: <br>%{value} (%{percent})')
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width='stretch')

with col2:
    fig = px.histogram(filtered_df, x=['Regional Office'], y='Quantity',
             color='Material Group', barmode='group',text_auto=True)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
    fig.update_layout(xaxis_title="",yaxis_title="")
    st.plotly_chart(fig)

with col3:
    fig = px.histogram(filtered_df, x='Regional Office', y='Quantity',
             color='Material Description',text_auto=True)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
    fig.update_layout(xaxis_title="",yaxis_title="")
    st.plotly_chart(fig)

col1, col2, col3 = st.columns(3)
with col1:
    fig = px.pie(filtered_df, values='Quantity',names = 'Plant Reg State', title="State Volumes")
    fig.update_traces(texttemplate='<b>%{label}</b>: <br>%{value} (%{percent})')
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig)
with col2:
    fig = px.histogram(filtered_df, x='Plant Reg State', y='Quantity',
             color='Material Group', barmode='group',text_auto=True)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
    fig.update_layout(xaxis_title="",yaxis_title="", showlegend=False)
    st.plotly_chart(fig)

with col3:
    fig = px.histogram(filtered_df, x='Plant Reg State', y='Quantity',
             color='Material Description',text_auto=True)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.8,xanchor="center"))
    
    fig.update_layout(xaxis_title="",yaxis_title="", showlegend=False)
    st.plotly_chart(fig)

fig = px.sunburst(filtered_df, 
                    path=['Plant Reg State', 'Material Group','Material Description'], 
                    values='Quantity',
                    title='Sales Distribution',
                    )
st.plotly_chart(fig, width='stretch')

# Display Dataframe
st.dataframe(filtered_df)