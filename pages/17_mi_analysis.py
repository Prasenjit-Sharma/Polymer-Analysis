import streamlit as st
import utilities
from reading_gsheet_data import read_data


utilities.apply_common_styles("Market Intelligence")

if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False

platts_df = read_data.read_mi_data()

min_date = platts_df['Date'].min()
max_date = platts_df['Date'].max()

# Options
with st.container(border=True):
    col1, col2, col3  = st.columns([1,1,3], vertical_alignment="bottom")
    with col1:
        date_from = st.date_input("From Date", format="DD/MM/YYYY", value=min_date)
    with col2:
        date_to = st.date_input("To Date", format="DD/MM/YYYY", value=max_date)
    with col3:
        chosen_metrics = st.selectbox("Seclect Metrics", utilities.METRIC_OPTIONS)
    
    # selected_metrics = utilities.return_selected_column_metrics(platts_df,chosen_metrics)
    filtered_platts_df = utilities.return_filtered_metric_df(platts_df,date_from, date_to,chosen_metrics)
    
# Results
with st.container(border=True):
    
    fig = utilities.draw_line_charts(filtered_platts_df)
    # Display the chart
    if fig:
        st.plotly_chart(fig, width="stretch")
    else:
        st.warning("No data columns selected to plot.")
    
    view_dataset = st.toggle("View DataSet", value=False)
    if view_dataset:
        utilities.mi_table(filtered_platts_df, chosen_metrics)