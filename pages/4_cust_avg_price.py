import streamlit as st
import pandas as pd
import numpy as np
from streamlit_calendar import calendar
from discount_calc import discount
from datetime import datetime
import utilities

# -------------------------------------------------
# Setup
# -------------------------------------------------
utilities.apply_common_styles("Material Pricing")
# In initial logged_in is False

df = st.session_state["Sales Data"]
discount_json = st.session_state["Discount Data"]

df = utilities.prepare_df_for_aggrid(df, columns_to_convert=["Fiscal Year"])

def prepare_material_price_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in ["Quantity", "Net Value of Billing item", "Net Discount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Final value at invoice level
    df["Final Value"] = (
        df["Net Value of Billing item"] -
        (df["Net Discount"] * df["Quantity"])
    )
    material_df = (
        df.groupby("Material Description", as_index=False)
        .agg(
            Total_Quantity=("Quantity", "sum"),
            Total_Final_Value=("Final Value", "sum")
        )
    )

    material_df["Final Price / kg"] = (
        material_df["Total_Final_Value"] /
        material_df["Total_Quantity"] /
        1000
    ).replace([float("inf"), -float("inf")], 0).fillna(0).round(2)

    return material_df

def render_material_price_metrics(material_df: pd.DataFrame):
    st.markdown("### 📊 Material-wise Final Price")

    cols = st.columns(4)

    for i, row in material_df.iterrows():
        with cols[i % 4]:
            st.metric(
                label=row["Material Description"],
                value=f"₹{row['Final Price / kg']:.2f}/kg",
                help=f"Total Qty: {row['Total_Quantity']:.0f} MT"
            )

def prepare_daily_material_calendar_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Billing Date"] = pd.to_datetime(df["Billing Date"])

    for col in ["Quantity", "Net Value of Billing item", "Net Discount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["Final Price"] = (
        df["Net Value of Billing item"] - (df["Net Discount"] * df["Quantity"])
    )

    daily = (
        df.groupby(
            ["Billing Date", "Material Description"],
            as_index=False
        )
        .agg(
            Total_Quantity=("Quantity", "sum"),
            Total_Final_Price=("Final Price", "sum")
        )
    )

    daily["Final Price / kg"] = (
        daily["Total_Final_Price"] /
        daily["Total_Quantity"] /
        1000
    ).replace([np.inf, -np.inf], 0).fillna(0).round(2)

    return daily

def render_material_legend(material_colors: dict):
    st.markdown("#### 🎨 Material Legend")

    cols = st.columns(5)
    for i, (mat, color) in enumerate(material_colors.items()):
        with cols[i % 5]:
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:8px;">
                    <div style="
                        width:14px;
                        height:14px;
                        background:{color};
                        border-radius:3px;">
                    </div>
                    <span style="font-size:13px;">{mat}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

def build_calendar_events(daily_df: pd.DataFrame):
    events = []

    # Color palette for different materials
    colors = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
        '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788'
    ]
    
    # Create color mapping for materials
    unique_materials = daily_df['Material Description'].unique()
    material_colors = {mat: colors[i % len(colors)] 
                      for i, mat in enumerate(unique_materials)}
        

    for _, r in daily_df.iterrows():
        event_title = (
            f"Qty: {r['Total_Quantity']:.2f}\n"
            f"₹{r['Final Price / kg']:.2f}/kg\n"
            f"{ r['Material Description']}"
        )
        events.append({
            "title": event_title,
            "start": r["Billing Date"].date().isoformat(),
            "allDay": True,
            "backgroundColor": material_colors[r['Material Description']],
            "borderColor": material_colors[r['Material Description']],
                      })

    return events, material_colors

def build_price_change_events(discount_json: dict) -> list[dict]:
    events = []

    if "Price Change" not in discount_json:
        return events

    for rec in discount_json["Price Change"]:
        start = pd.to_datetime(rec["start_date"])

        direction = rec.get("direction", "Increase")
        amount = rec.get("discount_amount", 0)
        material_groups = rec.get("material_groups",[])

        arrow = "▲" if direction == "Increase" else "▼"
        color = "#2ecc71" if direction == "Increase" else "#e74c3c"

        title = (f"{arrow} ₹{amount} {material_groups}")

        events.append({
            "title": title,
            "start": start.date().isoformat(),
            "allDay": True,
            "backgroundColor": color,
            "borderColor": color,
        })

    return events

# CAlendar 
if "calendar_date" not in st.session_state:
    st.session_state.calendar_date = datetime.today().date()



# -------------------------------------------------
# Filters
# -------------------------------------------------

with st.container(border=True):
    selected_year, selected_month, filter_df = utilities.period_selection(df)
    filtered_df = filter_df
    
monthly_discounts = discount.filter_discounts_for_month(discount_json, selected_year, selected_month)

if not monthly_discounts:
    st.warning("No discounts applicable for the selected month.")
    st.stop()

if filter_df.empty:
    st.warning(f"No sales data found for the period")
    st.stop()
else:
    df_with_discount = discount.apply_discount(filter_df,monthly_discounts, selected_year, selected_month)
    col1, col2, col3,col4,col5 = st.columns(5)

    with col1:
        cg = st.multiselect("Customer Group", df_with_discount["Sold-to Group"].unique())
        if not cg: cg = df_with_discount["Sold-to Group"].unique()
        df_with_discount = df_with_discount[df_with_discount["Sold-to Group"].isin(cg)]

    with col2:
        cust = st.multiselect("Customer", df_with_discount["Sold-to-Party Name"].unique())
        if not cust: cust = df_with_discount["Sold-to-Party Name"].unique()
        df_with_discount = df_with_discount[df_with_discount["Sold-to-Party Name"].isin(cust)]

    with col3:
        group = st.multiselect("Group", df_with_discount["Material Group"].unique())
        if not group: group = df_with_discount["Material Group"].unique()
        df_with_discount = df_with_discount[df_with_discount["Material Group"].isin(group)]

    with col4:
        grade = st.multiselect("Grade", df_with_discount["Material Description"].unique())
        if not grade: grade = df_with_discount["Material Description"].unique()
        df_with_discount = df_with_discount[df_with_discount["Material Description"].isin(grade)]

    with col5:
        dca = st.multiselect("DCA", df_with_discount["Plant Description"].unique())
        if not dca: dca = df_with_discount["Plant Description"].unique()
        df_with_discount = df_with_discount[df_with_discount["Plant Description"].isin(dca)]

    if len(df_with_discount) ==0 :
        st.warning("No Records Found")
        display_date = datetime.today()
    else:
        display_date = df_with_discount["Billing Date"].iloc[-1]

    calendar_options = {
    "initialView": "dayGridMonth",
    "initialDate": display_date.isoformat(),
    # "headerToolbar": {
    #     "left": "prev,next today",
    #     "center": "title",
    #     # "right": "dayGridMonth,timeGridWeek,timeGridDay",
    # },
    "editable": False,
    "selectable": False,
    "eventDisplay": "block",          # 🔑 IMPORTANT
    "dayMaxEventRows": True 
}
tab_excel, tab_calendar = st.tabs(["Pricing Chart", "Calendar with Pricing"])

with tab_calendar:
    daily_df = prepare_daily_material_calendar_df(df_with_discount)
    # Final Price
    events, material_colors = build_calendar_events(daily_df)
    render_material_legend(material_colors)

    # Price change tiles
    price_change_events = build_price_change_events(monthly_discounts)
    events = events + price_change_events

    # -------------------------------------------------
    # SINGLE render (SAFE)
    # -------------------------------------------------
    calendar_state = calendar(events=events,options=calendar_options)

    # Update visible month
    if calendar_state and "view" in calendar_state:
        start = pd.to_datetime(calendar_state["view"]["currentStart"])
        st.session_state.calendar_date = start.date()

with tab_excel:
    material_metrics_df = prepare_material_price_metrics(df_with_discount)
    with st.container(border=True):
        render_material_price_metrics(material_metrics_df)

    daily_df = prepare_daily_material_calendar_df(df_with_discount)
    
    utilities.render_excel_pivot(daily_df, key="daily_price")
