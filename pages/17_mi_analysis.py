import streamlit as st
import utilities
from reading_gsheet_data import read_data


utilities.apply_common_styles("Market Intelligence")

if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False

if "selected_metric" not in st.session_state:
    st.session_state["selected_metric"] = "PP Raffia CFR S Asia Weekly"

def sync_metric(widget_key):
    st.session_state["selected_metric"] = st.session_state[widget_key]

def return_chosen_metric(platts_df, key):
    metric_cols = [col for col in platts_df.columns if col != "Date"]
    selected_metric = st.session_state.get("selected_metric", metric_cols[0])
    default_index = (metric_cols.index(selected_metric)
        if selected_metric in metric_cols else 0)
    # if key not in st.session_state:
    #     st.session_state[key] = st.session_state["selected_metric"]
    # chosen_metrics = st.selectbox("Select Metrics", metric_cols, key=key,on_change=sync_metric,args=(key,)) 
    chosen_metrics = st.selectbox("Select Metrics", metric_cols, index=default_index,key=f"{key}_{default_index}")
    st.session_state["selected_metric"] = chosen_metrics

    return chosen_metrics


# for key in ("ts_metric","tsa_metric", "tes_metric", "tma_metric" "tmd_metric"):
    if key in st.session_state:
        st.session_state[key] = st.session_state["selected_metric"]

platts_df, mi_masters_df = read_data.read_mi_data()

min_date = platts_df['Date'].min()
max_date = platts_df['Date'].max()

tab_names = [
        "📋 Summary",
        "📉 Market Dynamics",
        "📊 Moving Averages",
        "📅 Seasonality Analysis",
        "📈 Historical Trends",
        "⚖️ Relative Value Analysis",
        "🔍 Price Driver Analysis",
        "🔗 Correlation Heatmap",
    ]

# Creating Tabs
(
    tab_exec_summary,
    tab_market_dynamics,
    tab_moving_average,
    tab_seasonality,
    tab_hist_trend,
    tab_spread_analysis,
    tab_price_driver,
    tab_correlation,
    
) = st.tabs(tab_names)

# Executive
with tab_exec_summary:
    with st.container(border=True):
        key = "tes_metric"
        chosen_metrics = return_chosen_metric(platts_df, key)
    
    with st.container(border=True):
        utilities.executive_summary(platts_df, date_from=min_date, date_to=max_date, commodity=chosen_metrics)

# Market Dynamics
with tab_market_dynamics:
    # Options
    with st.container(border=True):
        key = "tmd_metric"
        chosen_metrics = return_chosen_metric(platts_df, key)

        md_df = plot_df = utilities.return_market_dynamics_df(platts_df,date_from=min_date, date_to=max_date,commodity=chosen_metrics)

    with st.container(border=True):
        utilities.market_dynamics_summary(plot_df, chosen_metrics)

        fig_vol, fig_mom = utilities.draw_market_dynamics(plot_df)

        st.plotly_chart(fig_vol, width="stretch")

        st.plotly_chart(fig_mom, width="stretch")

        view_dataset = st.toggle("View DataSet", value=False, key="tmd_togdata")
        if view_dataset:
            utilities.mi_table(plot_df, chosen_metrics)

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
            key = "tma_metric"
            chosen_metrics = return_chosen_metric(platts_df, key)

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

# Seasonality
with tab_seasonality:
    with st.container(border=True):
        key = "ts_metric"
        chosen_metrics = return_chosen_metric(platts_df, key)

    monthly_df, seasonality_df, heatmap_df = utilities.return_seasonality_df(platts_df,chosen_metrics)

    with st.container(border=True):
        utilities.seasonality_summary(seasonality_df)

        fig_return, fig_vol, fig_heat = utilities.draw_seasonality(seasonality_df,heatmap_df)

        st.plotly_chart(fig_return, width="stretch")
        st.plotly_chart(fig_vol, width="stretch")    
        st.plotly_chart(fig_heat,width="stretch")

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
            chosen_metrics = st.selectbox("Seclect Metrics", unique_metrics ,index=1,key="tht_metric")
        
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

# Relative Value
with tab_spread_analysis:
    with st.container(border=True):
        chart_options = platts_df.columns.drop("Date").tolist()
        col1, col2 = st.columns(2)
        with col1:
            benchmark = st.selectbox("Select Benchmark",chart_options,index=0)
        with col2:
            key = "tsa_metric"
            chosen_metrics = return_chosen_metric(platts_df, key)

        utilities.spread_analysis(platts_df,chosen_metrics,benchmark)

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



                   