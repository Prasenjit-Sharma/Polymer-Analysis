import streamlit as st
import utilities
from reading_gsheet_data import read_data


utilities.apply_common_styles("Market Intelligence")

if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False

platts_df, mi_masters_df = read_data.read_mi_data()

min_date = platts_df['Date'].min()
max_date = platts_df['Date'].max()

tab_names = [
        "📋 Executive Summary",
        "📈 Historical Trends",
        "📊 Moving Averages",
        "🔍 Price Driver Analysis",
        "🔗 Correlation Heatmap",
        "⚖️ Relative Value Analysis",
        "📉 Market Dynamics",
        "📅 Seasonality Analysis"
    ]

# Creating Tabs
(
    tab_exec_summary,
    tab_hist_trend,
    tab_moving_average,
    tab_price_driver,
    tab_correlation,
    tab_spread_analysis,
    tab_market_dynamics,
    tab_seasonality,
) = st.tabs(tab_names)

# Historical Trends
with tab_hist_trend:
    # Options
    with st.container(border=True):
        col1, col2, col3  = st.columns([1,1,3], vertical_alignment="bottom")
        with col1:
            date_from = st.date_input("From Date", format="DD/MM/YYYY", value=min_date, 
                                      min_value=min_date, max_value=max_date, key="tht_dfrom")
        with col2:
            date_to = st.date_input("To Date", format="DD/MM/YYYY", value=max_date, 
                                    min_value=min_date, max_value=max_date, key="tht_dto")
        with col3:
            unique_metrics = (mi_masters_df["Metric Name"].dropna().astype(str)
                .str.strip().loc[lambda x: x != ""].unique().tolist())
            unique_metrics.insert(0, "Custom Metrics")
            chosen_metrics = st.selectbox("Seclect Metrics", unique_metrics, index=1,key="tht_metric")
        
        # selected_metrics = utilities.return_selected_column_metrics(platts_df,chosen_metrics)
        filtered_platts_df = utilities.return_filtered_metric_df(platts_df, mi_masters_df,date_from, date_to,chosen_metrics)
        
    # Results
    with st.container(border=True):
        
        fig = utilities.draw_line_charts(filtered_platts_df)
        # Display the chart
        if fig:
            st.plotly_chart(fig, width="stretch")
        else:
            st.warning("No data columns selected to plot.")
        
        view_dataset = st.toggle("View DataSet", value=False, key="tht_togdata")
        if view_dataset:
            utilities.mi_table(filtered_platts_df, chosen_metrics)

# Moving Average Tabs
with tab_moving_average:
    
    # Options
    with st.container(border=True):
        col1, col2, col3  = st.columns([1,1,3], vertical_alignment="bottom")
        with col1:
            date_from = st.date_input("From Date", format="DD/MM/YYYY", value=min_date, 
                                      min_value=min_date, max_value=max_date, key="tma_dfrom")
        with col2:
            date_to = st.date_input("To Date", format="DD/MM/YYYY", value=max_date, 
                                    min_value=min_date, max_value=max_date, key="tma_dto")
        with col3:
            metric_cols = [col for col in platts_df.columns if col != "Date"]
            chosen_metrics = st.selectbox("Select Metrics", metric_cols, key="tma_metric")

        ma_df = plot_df = utilities.return_filtered_ma_df(platts_df,date_from, date_to,chosen_metrics)
        
    # Results
    with st.container(border=True):
        utilities.moving_average_summary(plot_df, chosen_metrics)
        fig = utilities.draw_line_charts(plot_df,title="Moving Averages")
        # Display the chart
        if fig:
            st.plotly_chart(fig, width="stretch")
        else:
            st.warning("No data columns selected to plot.")
        
        view_dataset = st.toggle("View DataSet", value=False, key="tma_togdata")
        if view_dataset:
            # st.write(plot_df)
            utilities.mi_table(plot_df)

# Correlation
with tab_correlation:

    with st.container(border=True):
        chart_options = platts_df.columns.drop("Date").tolist()
        selected_metrics = st.multiselect("Select Custom Metrics",chart_options,max_selections=5,
                                          default=["Naphtha FOB Arab Gulf","PP Raffia CFR SE Asia Weekly"])
    
    with st.container(border=True):
        df = platts_df[selected_metrics]
        fig = utilities.correlation_heatmap(df)

        st.plotly_chart(fig, width="stretch")

with tab_price_driver:
    with st.container(border=True):
        chart_options = platts_df.columns.drop("Date").tolist()
        unique_feed = (mi_masters_df["Feedstock / Factors"].dropna().astype(str)
                .str.strip().loc[lambda x: (x != "")]
                .unique().tolist())
        feedstocks = st.multiselect("Select Factors / Feedstocks",unique_feed,default=unique_feed[0],key="tpd_feed")
        unique_margin_options = (mi_masters_df["Petrochemicals"].dropna().astype(str)
                .str.strip().loc[lambda x: (x != "")]
                .unique().tolist())
        polymers = st.multiselect("Select Petrochemicals",unique_margin_options,default=unique_margin_options[:3],key="tpd_poly")


        plot_df = utilities.price_driver_analysis(platts_df, feedstocks, polymers)
        utilities.render_excel_pivot(plot_df, key="tpd_excel")

with tab_spread_analysis:
    with st.container(border=True):
        chart_options = platts_df.columns.drop("Date").tolist()
        col1, col2 = st.columns(2)
        with col1:
            benchmark = st.selectbox("Select Benchmark",chart_options,index=0)
        with col2:
            commodity = st.selectbox("Select Commodity",chart_options,index=10)
        
        utilities.spread_analysis(platts_df,commodity,benchmark)

with tab_market_dynamics:
    # Options
    with st.container(border=True):
        col1, col2, col3  = st.columns([1,1,3], vertical_alignment="bottom")
        with col1:
            date_from = st.date_input("From Date", format="DD/MM/YYYY", value=min_date, 
                                      min_value=min_date, max_value=max_date, key="tmd_dfrom")
        with col2:
            date_to = st.date_input("To Date", format="DD/MM/YYYY", value=max_date, 
                                    min_value=min_date, max_value=max_date, key="tmd_dto")
        with col3:
            metric_cols = [col for col in platts_df.columns if col != "Date"]
            chosen_metrics = st.selectbox("Select Metrics", metric_cols, key="tmd_metric")

        md_df = plot_df = utilities.return_market_dynamics_df(platts_df,date_from, date_to,chosen_metrics)

    with st.container(border=True):
        utilities.market_dynamics_summary(plot_df, chosen_metrics)

        fig_vol, fig_mom = utilities.draw_market_dynamics(plot_df)

        st.plotly_chart(fig_vol, width="stretch")

        st.plotly_chart(fig_mom, width="stretch")

        view_dataset = st.toggle("View DataSet", value=False, key="tmd_togdata")
        if view_dataset:
            utilities.mi_table(plot_df, chosen_metrics)

with tab_seasonality:
    metric_cols = [col for col in platts_df.columns if col != "Date"]
    chosen_metrics = st.selectbox("Select Metrics", metric_cols, key="ts_metric")

    monthly_df, seasonality_df, heatmap_df = utilities.return_seasonality_df(platts_df,chosen_metrics)

    utilities.seasonality_summary(seasonality_df)

    fig_return, fig_vol, fig_heat = utilities.draw_seasonality(seasonality_df,heatmap_df)

    st.plotly_chart(fig_return, width="stretch")
    st.plotly_chart(fig_vol, width="stretch")    
    st.plotly_chart(fig_heat,width="stretch")

with tab_exec_summary:
    
    metric_cols = [col for col in platts_df.columns if col != "Date"]
    chosen_metrics = st.selectbox("Select Metrics", metric_cols, key="tes_metric") 
    
    utilities.executive_summary(platts_df, date_from=min_date, date_to=max_date, commodity=chosen_metrics)
                   