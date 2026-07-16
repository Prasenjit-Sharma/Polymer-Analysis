import streamlit as st
import utilities
from reading_gsheet_data import read_data


utilities.apply_common_styles("Market Intelligence")

if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False

platts_df = read_data.read_mi_data()

min_date = platts_df['Date'].min()
max_date = platts_df['Date'].max()



with st.container(border=True):
    col1, col2, col3  = st.columns([1,1,3], vertical_alignment="bottom")
    with col1:
        date_from = st.date_input("From Date", format="DD/MM/YYYY", value=min_date)
    with col2:
        date_to = st.date_input("To Date", format="DD/MM/YYYY", value=max_date)
    with col3:
        selected_metrics = st.multiselect("Seclect Metrics", utilities.MARGIN_OPTIONS, 
                                          default=utilities.MARGIN_OPTIONS[0])
    

    filtered_margin_df, margin_df, combined_df = utilities.return_filtered_margin_df(platts_df,date_from, date_to,selected_metrics)

with st.container(border=True):
    if st.toggle("View Price Details",value=False):
        fig = utilities.draw_line_charts(filtered_margin_df, title="Prices over Time")
    else:
        fig = utilities.draw_line_charts(margin_df, title="Margins over Time")
    
    
    if fig:
        st.plotly_chart(fig, width="stretch")
    else:
        st.warning("No data columns selected to plot.")
    
        
    view_dataset = st.toggle("View DataSet",value=False)
    if view_dataset:
        utilities.mi_table(combined_df)