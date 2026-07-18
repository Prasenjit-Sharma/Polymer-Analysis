from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import numpy as np
import pandas as pd
import plotly.express as px
from io import BytesIO
import streamlit as st
from mitosheet.streamlit.v1 import spreadsheet
import requests
from bs4 import BeautifulSoup
from reading_gsheet_data import read_data
import time
from datetime import datetime
from tvDatafeed import TvDatafeed, Interval
from sklearn.linear_model import LinearRegression

FISCAL_START = 4

month_order = ["April", "May", "June", 
               "July", "August", "September", "October", "November", "December","January", "February", "March"]

PREFERRED_MATERIAL_ORDER = ["HR033","HM120A","F01019S","F02020"]

def latest_data (df):
    display_year = df.iloc[-1]['Year']
    display_month = df.iloc[-1]['Month Name']
    display_month_no = df.iloc[-1]['Month']
    display_fiscal_year = get_fiscal_year(cal_month=display_month_no, cal_year=display_year)
    return display_year,display_fiscal_year, display_month,display_month_no

def get_fiscal_year(cal_month,cal_year):
        if cal_month >= FISCAL_START:
            fiscal_year = cal_year
        else:
            fiscal_year = cal_year - 1
        return fiscal_year

def enforce_string_ids(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"\.0$", "", regex=True)
                .str.strip()
            )
    return df

def parse_sheet_date(date_str):
    """Safely parse DD.MM.YYYY sheet names into a date object for comparison."""
    try:
        return datetime.strptime(date_str.strip(), "%d.%m.%Y").date()
    except ValueError:
        # Returns None if a sheet has a non-date name (e.g., "Sheet1", "Summary")
        return None
# Convert certain columns to strings
def prepare_df_for_aggrid(df, columns_to_convert=None):
    df_copy = df.copy()
    # Default columns that should be strings
    if columns_to_convert is None:
        columns_to_convert = [
            'Billing Document No.', 'Ship-to Party', 'Sold-to Party', 
            'Material', 'Plant', 'Fiscal Year', 'Year',
            'Month']
    
    # Convert columns that exist in the dataframe
    for col in columns_to_convert:
        if col in df_copy.columns:
            # df_copy[col] = df_copy[col].fillna(0).astype(int).astype(str)
            df_copy[col] = df_copy[col].apply(lambda x: str(int(float(x))) if pd.notna(x) else '')

    return df_copy

# Display Aggrid view of Group Pivot
def render_excel_pivot(df,key):
    df_copy = df.copy()
    df_copy = prepare_df_for_aggrid(df_copy)

    gb = GridOptionsBuilder.from_dataframe(df_copy)

    # Default column behavior
    gb.configure_default_column(
        enableRowGroup=True,
        enableValue=True,
        resizable=True,
        minWidth=120,     # prevents truncation
        maxWidth=350,     # prevents very wide columns
        wrapHeaderText=True,
        autoHeaderHeight=True,
    )

    # 🔑 Apply SUM to all numeric columns
    numeric_cols = df_copy.select_dtypes(include=["number"]).columns.tolist()
    for col in numeric_cols:
        gb.configure_column(
            col,
            aggFunc="sum",
            type=["numericColumn"],
            valueFormatter="x == null ? '' : x.toLocaleString('en-IN')"
        )
    # ✅ NEW: Configure string columns explicitly to prevent numeric formatting
    string_cols = df_copy.select_dtypes(include=["object"]).columns.tolist()
    for col in string_cols:
        gb.configure_column(
            col,
            type=["textColumn"],
            valueFormatter=None  # No formatter for string columns
        )
    
    # Aggregation of Columns in Max
    if "Final Price / kg" in df_copy.columns.tolist():
        gb.configure_column(
            "Final Price / kg",
            aggFunc="max",
            type=["numericColumn"],
            valueFormatter=None  # No formatter for string columns
        )

    # 🔑 Reliable sizing strategy (ONLY ONE THAT WORKS)
    size_to_fit_js = JsCode("""
    function(params) {
        params.api.sizeColumnsToFit();
    }
    """)

    gb.configure_grid_options(
        rowGroupPanelShow="always",
        groupDefaultExpanded=1,
        animateRows=True,
        suppressAggFuncInHeader=True,
        onGridReady=size_to_fit_js
    )

    grid_options = gb.build()

    AgGrid(
        df_copy,
        gridOptions=grid_options,
        height=600,
        theme="balham",
        enable_enterprise_modules=True,
        allow_unsafe_jscode=True,
        update_mode="NO_UPDATE",
        key=key
    )
    df_actions(df_copy,'polymer_sales_report.xlsx',key=key)

def draw_pie(df, values, names, title):
    fig = px.pie(df, values=values,names = names, title=title)
    fig.update_traces(texttemplate='<b>%{label}</b>: <br>%{value:.0f} (%{percent:.1%})')
    fig.update_layout(showlegend=False)
    return fig

def draw_sunburst(df,path,values,title):
    fig = px.sunburst(df, path=path, values=values, title=title)
    return fig

def prep_matdesc_category_order(df, color = None):
    category_orders = {}

    if color == "Material Description":
        # Append remaining materials after preferred ones
        remaining = [
            m for m in df[color].unique()
            if m not in PREFERRED_MATERIAL_ORDER
        ]

        category_orders[color] = PREFERRED_MATERIAL_ORDER + remaining
    return category_orders

def draw_histogram_month_quantity(df, color = None, title=None):
    # Get only months that exist in the data, in the correct order
    months_in_data = [m for m in month_order if m in df['Month Name'].unique()]
    # Base category order
    category_orders = {
        "Month Name": months_in_data
    }

    # --- Merge material description order (REUSED FUNCTION) ---
    category_orders.update(
        prep_matdesc_category_order(df, color)
    )
    fig = px.histogram(
            df.sort_values(by='Month Name'),
            x="Month Name",
            y="Quantity",
            # pattern_shape="Material Group",
            color=color,
            title=title,
            # barmode="group", # Groups the bars side-by-side
            category_orders=category_orders,
            text_auto=True
            )
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5),
        xaxis_title="",
        yaxis_title="",
        margin=dict(l=50, r=50, t=80, b=100)  # Adjust left margin
    )
    return fig

def draw_histogram_bar(df,x,y,color):

    category_orders = prep_matdesc_category_order(df, color)
    fig = px.histogram(df, x=x, y=y,
                    color=color, barmode='group',text_auto=True, category_orders=category_orders)
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5),
        xaxis_title="",
        yaxis_title="",
        margin=dict(l=50, r=50, t=80, b=100)  # Adjust left margin
    )
    return fig

def download_excel(df, filename='data.xlsx', button_label='📥 Download Excel', key='download_button',index=False):
    """
    Create a download button for formatted Excel file in Streamlit
    """
    buffer = BytesIO()
    
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=index, sheet_name='Sheet1')
        
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        
        # Header format
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        # Write headers with formatting
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Auto-fit columns
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
            worksheet.set_column(i, i, max_len)
    
    return buffer.getvalue()

def df_actions(df, filename='data.xlsx', key='df_actions',index=False):
    col1, col2 = st.columns(2)
    
    with col1:
        # Download button
        st.download_button(
            label="📥 Download Excel",
            data=download_excel(df=df, filename=filename, index=index),
            file_name=filename,
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            width="stretch",
            key=f'down_but_{key}'
        )
    
    with col2:
        open_mito = st.toggle("Explore in Excel", key=f'toggle_mito_{key}')
    
    # Show Mito if toggled
    if open_mito:
        st.divider()
        st.write("### 📊 Data Explorer")
        spreadsheet(df, key='show_mito_{key}')

def explore_with_mito(df, key='mito_explorer'):
    st.write("### 🔍 Data Explorer (Mito)")
    
    # Just open Mito, don't capture returns if not needed
    spreadsheet(df, key=key)

# Period Selection - Select Year, Select Month
def period_selection(df):
    # Creating options for Period Selection
    available_years = sorted(df["Year"].dropna().unique().astype(int))

    month_map = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December"
        }

    available_months = sorted(df["Month"].dropna().unique().astype(int))

    # st.subheader("Select Period for Discount Calculation")

    col1, col2 = st.columns(2)

    with col1:
        selected_year = st.selectbox(
                "Year",
                available_years,
                index=len(available_years) - 1
            )

    with col2:
        selected_month = st.selectbox(
                "Month",
                available_months,
                format_func=lambda m: month_map[m]
            )
    filtered_df = df[(df["Year"] == selected_year) & (df["Month"] == selected_month)].copy()
    return selected_year, selected_month, filtered_df

# Applying styles to all pages
def apply_common_styles(title):
    st.set_page_config(layout="wide",initial_sidebar_state="collapsed") 
    st.markdown(f"### {title}")
    st.markdown("""
        <style>
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 3rem !important;
        }
        </style>
    """,
    unsafe_allow_html=True)

# Render Discount JSON
def render_discount_json(value):
    """Render any JSON value cleanly"""
    if isinstance(value, dict):
        for k, v in value.items():
            st.markdown(f"**{k}**")
            render_discount_json(v)

    elif isinstance(value, list):
        if len(value) == 0:
            st.write("—")

        # List of dicts → table
        elif all(isinstance(i, dict) for i in value):
            df = pd.DataFrame(value)
            st.table(df)

        # List of primitives → bullets
        else:
            for i in value:
                st.write(f"- {i}")

    else:
        st.write(value)

# Scrapping
@st.cache_data(ttl=3600,show_spinner=False,show_time=True)
def fetch_price_news():
    url = "https://www.plastemart.com/whats-new-plastics-industry"
    # Using a common browser Header to prevent being blocked
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Target the specific ID and classes from your example
        product_container = soup.find('div', id='products')
        if not product_container:
            return []

        news_list = []
        # Find each news card
        items = product_container.find_all('div', class_='item')

        for item in items:
            caption = item.find('div', class_='caption')
            if caption:
                # 1. Extract the Date
                date_div = caption.find('div', class_='news-date')
                date_val = date_div.get_text(strip=True) if date_div else "N/A"
                
                # 2. Extract the News Text (cleaning up the HTML)
                # We remove the date_div from the caption to get only the text
                if date_div:
                    date_div.extract() 
                
                # Use separator to keep <br> as spaces
                news_text = caption.get_text(separator=" ", strip=True)
                
                # Use the first line as a title for the UI
                title = news_text.split('.')[0] if '.' in news_text else news_text[:60] + "..."

                news_list.append({
                    "Date": date_val,
                    "Title": title,
                    "Details": news_text
                })
        
        return news_list
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return []

@st.cache_data(ttl=3600,show_spinner=False,show_time=True)
def get_market_metrics():
    """
    Fetches latest rates for Crude and USD-INR directly from TradingView feeds.
    """
    try:
        # Initialize the feed anonymously
        tv = TvDatafeed()
        
        # Define tickers and their respective primary exchange mappings
        # TV uses specific exchange prefixes: 'TVC' (TradingView Charts) or 'FX_IDC'
        instruments = [
            {"name": "Brent Crude", "symbol": "UKOIL", "exchange": "TVC"},
            {"name": "WTI Crude", "symbol": "USOIL", "exchange": "TVC"},
            {"name": "USD-INR", "symbol": "USDINR", "exchange": "FX_IDC"},
            {"name": "Nifty 50", "symbol": "NIFTY", "exchange": "NSE"}
        ]
        
        metrics = {}
        
        for inst in instruments:
            # Fetch the single latest 1-minute interval bar to get the live price
            data = tv.get_hist(
                symbol=inst["symbol"],
                exchange=inst["exchange"],
                interval=Interval.in_1_minute,
                n_bars=2
            )
            
            if data is not None and not data.empty:
                # The last row [-1] is the active/live candle price
                current_val = data['close'].iloc[-1]
                # The previous row [-2] provides a baseline to calculate a dynamic trend
                prev_val = data['close'].iloc[-2]
                
                change = current_val - prev_val
                pct_change = (change / prev_val) * 100 if prev_val != 0 else 0
                
                metrics[inst["name"]] = {
                    "value": round(current_val, 2),
                    "change": round(change, 2),
                    "pct_change": round(pct_change, 2)
                }
                
        return metrics

    except Exception as e:
        st.error(f"TradingView connection error")
        return None

def display_market_metrics():
    # Fetch metrics globally
    with st.container(border=True):
        try:
            market_data = get_market_metrics()

            if market_data:
                m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                
                with m_col1:
                    st.metric(
                        label="🇮🇳 Nifty 50 Index",
                        value=f"{market_data['Nifty 50']['value']:,}",  # Formats number with commas
                        delta=f"{market_data['Nifty 50']['change']} ({market_data['Nifty 50']['pct_change']}%)"
                    )

                with m_col2:
                    st.metric(
                        label="💵 USD - INR Spot",
                        value=f"₹{market_data['USD-INR']['value']}",
                        delta=f"{market_data['USD-INR']['change']} ({market_data['USD-INR']['pct_change']}%)",
                        delta_color="inverse"
                    )
                    
                with m_col3:
                    st.metric(
                        label="🛢️ Brent Crude",
                        value=f"${market_data['Brent Crude']['value']}",
                        delta=f"${market_data['Brent Crude']['change']} ({market_data['Brent Crude']['pct_change']}%)"
                    )
                    
                with m_col4:
                    st.metric(
                        label="🇺🇸 WTI Crude",
                        value=f"${market_data['WTI Crude']['value']}",
                        delta=f"${market_data['WTI Crude']['change']} ({market_data['WTI Crude']['pct_change']}%)"
                    )   
        except:
            st.write("")
# Producer Pricing
COMPANIES = ["RIL","OPAL","HMEL","IOCL","GAIL","MRPL","NAYARA","HPCL","HPL"]
FAMILY = ["PE", "PP"]
CATEGORY = ["RAFFIA", "IM", "LL1", "LL2", "HD IM"]
PRICE_POINT_MAP = {
    "RIL" : ["Depot", "Plant"],
    "OPAL": ["Depot", "Plant"],
    "HMEL": ["Depot", "Plant"],
    "IOCL": ["Depot", "Plant", "Warehouse"],
    "GAIL": ["Depot", "Plant"],
    "MRPL": ["Depot", "Plant"],
    "NAYARA": ["Depot", "Plant"],
    "HPCL": ["Depot"],
    "HPL": ["Depot", "Plant"],
}
SPECIAL_FREIGHT_COMPANIES = ["HMEL", "OPAL", "HPL", "NAYARA","MRPL","GAIL"]

def get_price(df, grade_input, location_input):

    # -----------------------------
    # Find matching column
    # -----------------------------
    matching_columns = [
        col for col in df.columns
        if grade_input.lower() in str(col).lower()
    ]

    if not matching_columns:
        return None, "No matching grade found"

    grade_column = matching_columns[0]

    # -----------------------------
    # Find matching row
    # -----------------------------
    # matching_rows = df[
    #     df["Location"].astype(str).str.lower() == location_input.lower()
    # ]
    matching_rows = df[
    df["Location"].astype(str).str.lower().str.contains(location_input.lower(), na=False)
    ]

    if matching_rows.empty:
        return None, "No matching location found"

    # -----------------------------
    # Get price
    # -----------------------------
    price = matching_rows.iloc[0][grade_column]

    return price, "Match Found"

def get_freight(df, location_input):

    matching_rows = df[
        df["Location"].astype(str).str.lower() == location_input.lower()
    ]

    if matching_rows.empty:
        return None

    freight = matching_rows.iloc[0]["Freight"]

    return freight

def get_spreadsheet_name(company,mat_family,price_point):
    spreadsheet_name = (f"{company}_{mat_family}_{price_point}").upper()
    freight_sheet_name = (f"{company}_freight").upper()
    return spreadsheet_name,freight_sheet_name

# OLD GROUPS CREATE

def add_row():
    row_id = str(time.time_ns())
    st.session_state.rows.append(
        {
            "id": row_id,
            "company": "",
            "family": "",
            "category":"",
            "grade": "",
            "location": "",
            "price_point": "",
            "delivery_location": ""
        }
    )

def delete_row(row_id):
    st.session_state.rows = [r for r in st.session_state.rows if r["id"] != row_id]

def clear_pricing_data():
    st.session_state.pricing_df = []
    st.session_state.rows = []
    st.session_state.selected_group_df = []

def refresh_group():
    st.session_state.group_df, st.session_state.productgroup_df, st.session_state.locationgroup_df = read_data.read_groups_data()

@st.fragment
def new_render_create_group():
    # Initialize if empty
    if "rows" not in st.session_state or not st.session_state.rows:
        st.session_state.rows = []
        add_row()
    with st.container(border=True):
        col1, col2, col3 = st.columns(3, vertical_alignment="bottom")
        with col1:
            selected_family = st.selectbox("Family",FAMILY,key="family")
        with col2:
            selected_category = st.selectbox("Category",CATEGORY,key="category")
        with col3:
            st.button("Clear Data", type="secondary", width="stretch", on_click=clear_pricing_data)
        
    with st.container(border=True):
        # Read directly from session_state so it picks up additions/deletions instantly
        for row in st.session_state.rows:
            row_id = row["id"]
            cols = st.columns([1, 1, 1, 1, 1, 0.4],vertical_alignment="bottom")

            # CRITICAL: Use row_id instead of loop index for all keys
            row["company"] = cols[0].selectbox("Company",COMPANIES,key=f"company_{row_id}")
            row["family"] = selected_family
            row["category"] = selected_category
            row["grade"] = cols[1].text_input("Grade",value=row["grade"],key=f"grade_{row_id}")
            row["location"] = cols[2].text_input("Location",value=row["location"],key=f"location_{row_id}")
            available_price_points = PRICE_POINT_MAP.get(row["company"], [])
            row["price_point"] = cols[3].selectbox("Price Point",available_price_points,key=f"price_point_{row_id}")

            if row["price_point"] == "Plant" and row["company"] in SPECIAL_FREIGHT_COMPANIES:
                row["delivery_location"] = cols[4].text_input("Delivery Location",
                    value=row.get("delivery_location", ""),key=f"delivery_location_{row_id}")
            else:
                row["delivery_location"] = ""

            with cols[5]:
                st.button("❌",key=f"delete_button_{row_id}",on_click=delete_row, args=(row_id,))

        st.button("➕ Add Row", on_click=add_row)        
        # save_group()

def save_group():
    SPREADSHEET_URL = st.secrets["pricing"]["GROUP_MASTER_SHEET"]
    col1, col2 = st.columns(2, vertical_alignment="bottom")
    with col1:
        group_name = st.text_input("Group Name",key="group_name")
    with col2:
        save_clicked = st.button("💾 Save Group", width="stretch", type="primary")
    

    if save_clicked:
        spreadsheet,sheet_names = read_data.get_sheet_names(SPREADSHEET_URL)
        worksheet = spreadsheet.worksheet("Groups")
        rows_to_save = []

        for row in st.session_state.rows:

            rows_to_save.append([
                group_name,
                row["company"],
                row["family"],
                row["category"],
                row["grade"],
                row["location"],
                row["price_point"],
                row["delivery_location"]
            ])

        worksheet.append_rows(rows_to_save)
        read_data.read_groups_data.clear()
        st.success("Group saved successfully")

# Discount Screen
@st.fragment
def render_interactive_pricing_zone(group_df):
    with st.container(border=True):

        col1, col2, col3, col4 = st.columns(4,vertical_alignment="top")
        temp_df = group_df

        with col1:
            price_date = st.date_input( "Price Date", format="DD/MM/YYYY")
        
        with col2:
            all_family = sorted(temp_df["family"].unique())
            selected_family = st.selectbox("Family", all_family)
            temp_df = temp_df[temp_df["family"]== selected_family]

        with col3:
            all_category = sorted(temp_df["category"].unique())
            selected_category = st.selectbox("category", all_category)
            temp_df = temp_df[temp_df["category"]== selected_category]

        with col4:
            selected_qty = st.number_input("Quantity",min_value=0,max_value=9999)
        
        col1, col2, col3 = st.columns([1,1,2])
        with col1:
            all_location = sorted(temp_df["location"].unique())
            selected_location = st.selectbox("Location", all_location)
            temp_df = temp_df[temp_df["location"]== selected_location]
            
        with col2:
            all_price_point = sorted(temp_df["price_point"].unique())
            selected_price_point = st.selectbox("Price Point", all_price_point)
            temp_df = temp_df[temp_df["price_point"]== selected_price_point]
            # st.write(temp_df)

        with col3:
            all_groups = sorted(temp_df["group_name"].unique())
            selected_group = st.selectbox("Group Name", all_groups)


        with col1:
            show_published = st.toggle("Published Discounts", value=True, key="frag_show_pub")
        with col2:
            
            if (st.session_state["is_logged_in"]): #"is_logged_in" in st.session_state:
                show_unpublished = st.toggle("UnPublished Discounts", key="frag_show_unpub")
            else:
                show_unpublished = False
        
        with col3:
            submit_price = st.button("Get Prices",type="primary",width="stretch")

    if submit_price:
        
        with st.container(border=False):
            selected_group_df = group_df[group_df["group_name"]== selected_group].reset_index(drop=True)
            selected_group_df["Price Circular Date"]= selected_group_df["Freight Circular Date"]= ""
            st.session_state.selected_group_df = selected_group_df
            get_discounts(selected_group_df, selected_family, selected_qty, price_date, show_published, show_unpublished)
            pricing_editor_fragment()
            

## NEW GROUP CREATE
@st.fragment
def render_find_group_price():
    with st.container(border=True):
        if st.button(":material/change_circle: Refresh Groups", key="refresh_find"):
            refresh_group()
        # Product Group
        with st.container():
            col1, col2, col3, col4 = st.columns(4,vertical_alignment="top")
            productgroups = st.session_state.productgroup_df
            locationgroups = st.session_state.locationgroup_df
            with col1:
                price_date = st.date_input( "Price Date", format="DD/MM/YYYY")
            with col2:
                selected_family = st.selectbox("Family", FAMILY)
                productgroups = productgroups[productgroups["family"] == selected_family]

            with col3:
                unique_category = (productgroups["category"].unique())
                selected_category = st.selectbox("Category", unique_category)
                productgroups = productgroups[productgroups["category"]== selected_category]

            with col4:
                unique_productgroups = sorted(productgroups["productgroupname"].unique())
                selected_productgroup = st.selectbox("Product Group", unique_productgroups)
                productgroups = productgroups[productgroups["productgroupname"]== selected_productgroup]

        # Location Group
        with st.container():
            col1, col2, col3, col4 = st.columns([1,1,1,1])
            with col1:
                unique_pricepoint = sorted(locationgroups["price_point"].unique())
                selected_pricepoint = st.selectbox("Price Point", unique_pricepoint)
                locationgroups = locationgroups[locationgroups["price_point"]== selected_pricepoint]
                
            with col2:
                unique_location = sorted(locationgroups["location"].unique())
                selected_location = st.selectbox("Location", unique_location)
                locationgroups = locationgroups[locationgroups["location"]== selected_location]
                # st.write(temp_df)

            with col3:
                df = st.session_state.locationgroup_df
                unique_locationgroups = sorted(locationgroups["locationgroupname"].unique())
                selected_locationgroup = st.selectbox("Location Group", unique_locationgroups)
                locationgroups = df[df["locationgroupname"]== selected_locationgroup]

            with col4:
                selected_qty = st.number_input("Quantity",min_value=0,max_value=9999)
        
        # Buttons
        with st.container():
            col1, col2, col3 = st.columns([1,1,2])
            with col1:
                show_published = st.toggle("Published Discounts", value=True, key="frag_show_pub")
            with col2:
                
                if (st.session_state["is_logged_in"]): #"is_logged_in" in st.session_state:
                    show_unpublished = st.toggle("UnPublished Discounts", key="frag_show_unpub")
                else:
                    show_unpublished = False
            
            with col3:
                submit_price = st.button("Get Prices",type="primary",width="stretch")

        if submit_price:
            # Perform an inner merge on the 'company' column
            # st.write(productgroups, locationgroups)
            selected_group_df = pd.merge(productgroups,
                locationgroups[['company', 'price_point', 'location', 'delivery_location']],
                on='company',how='inner')
            selected_group_df["Price Circular Date"]= selected_group_df["Freight Circular Date"]= ""
            st.session_state.selected_group_df = selected_group_df
            get_discounts(selected_group_df, selected_family, selected_qty, price_date, show_published, show_unpublished)
            pricing_editor_fragment()

# Isolated fragment container
@st.fragment
def pricing_editor_fragment():
    with st.container():
        # Wrap the block in a form to prevent live keystroke refreshes
        with st.form(key="editor"):
            edited_df = st.data_editor(
                st.session_state.pricing_df, 
                width="stretch",
                hide_index=False,
                disabled= ["Grade", "Basic Price",  "Net Price"],
                key="pricing_editor"
            )
            col1, col2 = st.columns([1,2],vertical_alignment="center")
            with col1:
                # When clicked, ONLY this fragment reruns!
                if st.form_submit_button("🔄 Recalculate", width="stretch", type="primary"):
                    
                    # Restore Basic Price
                    edited_df.loc["Basic Price"] = st.session_state.pricing_df.loc["Basic Price"]

                    # Filter rows to calculate deductions
                    deduction_rows = [
                        r for r in edited_df.index
                        if r not in ["Grade", "Basic Price", "Freight", "Net Price"]
                    ]

                    # Calculate new Net Price
                    edited_df.loc["Net Price"] = (
                        edited_df.loc["Basic Price"]
                        + edited_df.loc["Freight"]
                        - edited_df.loc[deduction_rows].sum()
                    )

                    # Update Session State
                    st.session_state.pricing_df = edited_df
                    
                    # Force the data_editor inside this fragment to visually refresh immediately
                    st.rerun(scope="fragment")
            with col2:
                st.info("Note - All fields in table above are editable. Please edit and press Recalculate for new Net Price.")
        col1, col2 = st.columns([2,1])
        with col1:
            excel_df = st.session_state.pricing_df
            excel_df.index.name = "Description"
            df_actions(excel_df,filename='Polymer Pricing.xlsx', index=True)
        with col2:
            is_view_group = st.toggle("View Pricing Group")
                
        if is_view_group: 
            st.dataframe(st.session_state.selected_group_df,width="stretch",hide_index=True)
     
@st.fragment
def render_create_group():

    # 1. Base Selectors
    with st.container():
        col1, col2 = st.columns([1, 2])
        with col1:
            group_type = st.radio("Choose Group", ["Product Group", "Location Group"], horizontal=True)
        with col2:
            st.info("Please refer Price and Freight Circulars for creating groups.",icon=":material/info:",)

    # --- BLOCK A: PRODUCT GROUP WORKING WORKSPACE ---
    if group_type == "Product Group":
        # Initialize internal session dataframe if missing
        if "new_product_df" not in st.session_state:
            st.session_state["new_product_df"] = pd.DataFrame(
                columns=[ "company", "grade"])
        with st.container(border=True):
            col1, col2, col3 = st.columns(3, vertical_alignment="bottom")
            with col1:
                selected_family = st.selectbox("Family", FAMILY, key="family")
            with col2:
                df_source = st.session_state.productgroup_df
                unique_category = df_source[df_source["family"] == selected_family]["category"].unique()
                selected_category = st.selectbox("Category", unique_category, key="category",accept_new_options=True)
            with col3:
                if st.button("Clear Data", type="secondary", width="stretch"):
                    st.session_state["new_product_df"] = pd.DataFrame(
                        columns=["company", "grade"])
                    st.rerun(scope="fragment")

        with st.container(border=True):
            st.markdown("#### 📦 Enter Product Rows")
            session_dataframe_key = "new_product_df"
            column_config={
                    "company": st.column_config.SelectboxColumn("Company", options=COMPANIES, required=True),
                    "grade": st.column_config.TextColumn("Grade Code", required=True),
                    # "_index":None
                }
            session_edit_key="prod_editor_grid"
            render_data_editor(session_dataframe_key,session_edit_key,column_config)
            
        

    # --- BLOCK B: LOCATION GROUP WORKING WORKSPACE ---
    elif group_type == "Location Group":
        if "new_location_df" not in st.session_state:
            st.session_state["new_location_df"] = pd.DataFrame(
                columns=[ "company", "location", "delivery_location"])

        with st.container(border=True):
            col1, col2, col3 = st.columns(3, vertical_alignment="bottom")
            with col1:
                df_source = st.session_state.locationgroup_df
                unique_pricepoint = df_source["price_point"].unique()
                selected_pricepoint = st.selectbox("Price Point", unique_pricepoint, key="pricepoint")
            with col3:
                if st.button("Clear Data", type="secondary", width="stretch"):
                    st.session_state["new_location_df"] = pd.DataFrame(
                        columns=[ "company", "location", "delivery_location"])
                    st.rerun(scope="fragment")

        with st.container(border=True):
            st.markdown("#### 📍 Enter Location Rows")
            session_dataframe_key = "new_location_df"
            # Determine if delivery location should be open or closed based on your rules
            is_plant = (selected_pricepoint == "Plant")
            column_config = {
                    "company": st.column_config.SelectboxColumn("Company", options=COMPANIES, required=True),
                    "location": st.column_config.TextColumn("Location"),
                    "delivery_location": st.column_config.TextColumn(
                        "Delivery Location", disabled=not is_plant,),}  # Lock if price_point isn't Plant
                        
            session_edit_key =  "loc_editor_grid"
            render_data_editor(session_dataframe_key,session_edit_key,column_config)
            

    with st.container():    
        SPREADSHEET_URL = st.secrets["pricing"]["GROUP_MASTER_SHEET"]
        col1, col2 = st.columns(2, vertical_alignment="bottom")
        with col1:
            group_name = st.text_input("Group Name",key="group_name")
            
        with col2:
            save_clicked = st.button("💾 Save Group", width="stretch", type="primary")
        
        if save_clicked:       
            if group_type == "Product Group":
                new_group_df = pd.DataFrame(st.session_state["new_product_df"])
                new_group_df["productgroupname"] = group_name
                new_group_df["family"] = selected_family
                new_group_df["category"] = selected_category
                new_order = ['productgroupname', 'family', 'category','company','grade']
                new_group_df = new_group_df[new_order]
                read_data.append_data(SPREADSHEET_URL,"ProductGroup",df=new_group_df)
                st.success("Group saved successfully")  

            elif group_type == "Location Group":
                new_group_df = pd.DataFrame(st.session_state["new_location_df"])
                new_group_df["locationgroupname"] = group_name
                new_group_df["price_point"] = selected_pricepoint
                new_order = ['locationgroupname', 'price_point', 'company','location','delivery_location']
                new_group_df = new_group_df[new_order].fillna("")
                read_data.append_data(SPREADSHEET_URL,"LocationGroup",df=new_group_df)
                st.success("Group saved successfully")
            st.session_state.group_df, st.session_state.productgroup_df, st.session_state.locationgroup_df = read_data.read_groups_data()

def render_data_editor(session_dataframe_key,session_edit_key,column_config):
    # Render the data editor grid
    base_data = st.session_state[session_dataframe_key]
    # st.session_state[session_dataframe_key].reset_index(drop=True)
    updated_config = dict(column_config)
    updated_config["_index"] = None

    st.data_editor(
        base_data,
        column_config=updated_config,
        num_rows="dynamic",
        # hide_index=True,
        width="stretch",
        key=session_edit_key,
        on_change=update_df,
        args=(session_dataframe_key, session_edit_key)
    )
    
    # st.session_state[session_dataframe_key] = edited_prod

# Define a callback function to handle the edits immediately during the rerun
def update_df(session_dataframe_key,session_edit_key):
    # Grab the raw mutations directly from the data editor's state
    raw_editor_state = st.session_state[session_edit_key]
    if not raw_editor_state:
        return

    # Reconstruct the dataframe using Streamlit's built-in state processor
    # This applies additions, edits, and deletions instantly in memory
    base_df = st.session_state[session_dataframe_key].copy()

    # 1. Handle Added Rows
    for added in raw_editor_state.get("added_rows", []):
        new_row = pd.DataFrame([added])
        base_df = pd.concat([base_df, new_row], ignore_index=True)

    # 2. Handle Edited Rows
    for idx_str, edits in raw_editor_state.get("edited_rows", {}).items():
        idx = int(idx_str)
        for col, val in edits.items():
            base_df.at[idx, col] = val

    # 3. Handle Deleted Rows
    deletions = raw_editor_state.get("deleted_rows", [])
    if deletions:
        base_df = base_df.drop(index=deletions).reset_index(drop=True)

    # Save the synchronized dataframe back into your state
    st.session_state[session_dataframe_key] = base_df

def render_view_group():
    group_type = st.radio("Choose Group", ["Product Group", "Location Group"], horizontal=True, key="view_grp")
    
    productgroups = st.session_state.productgroup_df
    locationgroups = st.session_state.locationgroup_df

    if group_type == "Product Group":
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns(4,vertical_alignment="bottom")    
            with col1:
                selected_family = st.selectbox("Family", FAMILY, key="view_grp_fam")
                productgroups = productgroups[productgroups["family"] == selected_family]

            with col2:
                unique_category = sorted(productgroups["category"].unique())
                selected_category = st.selectbox("Category", unique_category, key="view_grp_cat")
                productgroups = productgroups[productgroups["category"]== selected_category]

            with col3:
                unique_productgroups = sorted(productgroups["productgroupname"].unique())
                selected_productgroup = st.selectbox("Product Group", unique_productgroups, key="view_grp_grp")
                productgroups = productgroups[productgroups["productgroupname"]== selected_productgroup]

            with col4:
                view_button = st.button("View Group", type="primary")
            if view_button:
                st.dataframe(productgroups, hide_index=True)
        

    if group_type == "Location Group":
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns(4,vertical_alignment="bottom")
            with col1:
                unique_pricepoint = sorted(locationgroups["price_point"].unique())
                selected_pricepoint = st.selectbox("Price Point", unique_pricepoint, key="view_loc_pp")
                locationgroups = locationgroups[locationgroups["price_point"]== selected_pricepoint]
                
            with col2:
                unique_location = sorted(locationgroups["location"].unique())
                selected_location = st.selectbox("Location", unique_location, key="view_loc_loc")
                locationgroups = locationgroups[locationgroups["location"]== selected_location]

            with col3:
                df = st.session_state.locationgroup_df
                unique_locationgroups = sorted(locationgroups["locationgroupname"].unique())
                selected_locationgroup = st.selectbox("Location Group", unique_locationgroups,key="view_loc_grp")
                locationgroups = df[df["locationgroupname"]== selected_locationgroup]   

            with col4:
                view_button = st.button("View Group", type="primary")
            if view_button:
                st.dataframe(locationgroups, hide_index=True) 
@st.fragment
def render_delete_group():
    SPREADSHEET_URL = st.secrets["pricing"]["GROUP_MASTER_SHEET"]
    with st.container():
        col1, col2, col3 = st.columns([1,2,0.5],vertical_alignment="center")
        with col1:
            group = st.radio("Choose Group",["Product Group","Location Group"], horizontal=True,key="group_delete")
        with col2:
            st.info("Groups once deleted cannot be restored.", icon=":material/info:")
        with col3:
            if st.button(":material/change_circle: Refresh Groups",key="refresh_delete"):
                refresh_group()

        if group == "Product Group":
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([1,1,2,2], vertical_alignment="bottom")
                with col1:
                    selected_family = st.selectbox("Family",FAMILY,key="family_delete")
                with col2:
                    df = st.session_state.productgroup_df
                    df = df[df["family"] == selected_family]
                    unique_category = df["category"].unique()
                    selected_category = st.selectbox("Category",unique_category,key="category_delete")
                with col3:
                    df = df[df["category"] == selected_category]
                    unique_groups = df["productgroupname"].unique()
                    selected_group = st.selectbox("Category",unique_groups,key="groups_delete")
                    df = df[df["productgroupname"]==selected_group]
                with col4:
                    submit_button = st.button("Delete Group",width="stretch",type="primary")
                if submit_button:
                    read_data.delete_rows(SPREADSHEET_URL,"ProductGroup","productgroupname",selected_group)
                    st.success("Group deleted successfully")
                    st.session_state.group_df, st.session_state.productgroup_df, st.session_state.locationgroup_df = read_data.read_groups_data()
        
        elif group == "Location Group":
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([1,1,2,2], vertical_alignment="bottom")
                with col1:
                    # st.write(st.session_state.locationgroup_df)
                    df = st.session_state.locationgroup_df
                    unique_pricepoint = df["price_point"].unique()
                    selected_pricepoint = st.selectbox("Price Point",unique_pricepoint,key="pricepoint_delete")
                with col2:
                    df = df[df["price_point"] == selected_pricepoint]
                    unique_location = df["location"].unique()
                    selected_location = st.selectbox("Location",unique_location,key="location_delete")
                with col3:
                    df = df[df["location"] == selected_location]
                    unique_groups = df["locationgroupname"].unique()
                    selected_group = st.selectbox("Group",unique_groups,key="locgroups_delete")
                    df = df[df["locationgroupname"]==selected_group]
                with col4:
                    submit_button = st.button("Delete Group",width="stretch",type="primary")
                if submit_button:
                    read_data.delete_rows(SPREADSHEET_URL,"LocationGroup","locationgroupname",selected_group)
                    st.success("Group deleted successfully")
                    read_data.read_groups_data()
                    st.rerun(scope="fragment")
                    st.session_state.group_df, st.session_state.productgroup_df, st.session_state.locationgroup_df = read_data.read_groups_data()

# DISCOUNT
def get_discount_dataframe(selected_family, show_published, show_unpublished):
    spreadsheet_url = st.secrets["pricing"]["PUBLISHED_DISCOUNT_MASTER_SHEET"]
    published_discount_df = read_data.read_discount_data(spreadsheet_url,selected_family)

    spreadsheet_url = st.secrets["pricing"]["UNPUBLISHED_DISCOUNT_MASTER_SHEET"]
    unpublished_discount_df = read_data.read_discount_data(spreadsheet_url,selected_family)
    
    if show_published and show_unpublished:
        # Merge both dataframes vertically since they share identical headers
        discount_df = pd.concat([published_discount_df, unpublished_discount_df], ignore_index=True)
        
    elif show_published:
        discount_df = published_discount_df
    
    elif show_unpublished:
        discount_df = unpublished_discount_df
        
    else:
        # Create a completely blank dataframe matching the expected schema headers
        discount_df = pd.DataFrame(columns=published_discount_df.columns)

    # discount_df = published_discount_df.copy()

    return discount_df
# Calculate Prices and Discounts
def get_discounts(selected_group_df, selected_family, selected_qty, price_date,
                             show_published, show_unpublished):
    
    companies = selected_group_df["company"].unique()
    pricing_df = pd.DataFrame( columns=companies)
   
    # pricing_df.loc["Grade", :] = selected_group_df["grade"].values
    # pricing_df = pd.DataFrame(0.0, index=PRICE_ROWS, columns=companies)
    
      
    discount_df = get_discount_dataframe(selected_family,show_published, show_unpublished)
    discount_df = discount_df[(discount_df["Date From"] <= price_date) &
                    (discount_df["Date To"] >= price_date)]
    
    # 1. 🚀 INITIALIZE PROGRESS BAR CONTEXT
    total_rows = len(selected_group_df)
    progress_text = "Fetching pricing matrix structures. Please wait..."
    progress_bar = st.progress(0, text=progress_text)

    for idx, row in selected_group_df.iterrows():

        # 2. UPDATE PROGRESS PERCENTAGE DYNAMICALLY
        current_percentage = int(((idx + 1) / total_rows) * 100)
        progress_bar.progress(current_percentage, text=f"{progress_text} ({current_percentage}%)")

        company = row["company"]
        family = row["family"]
        grade = row["grade"]
        location = row["location"]
        price_point = row["price_point"]
        delivery_location = row["delivery_location"]

        # PRICE
        price = 0
        try:
            spreadsheet_name, freight_sheet_name = (
                get_spreadsheet_name(company,family,price_point))
            price_df, price_circular_date = (
                read_data.read_pricing_data_cached(spreadsheet_name,price_date))
            price, msg = get_price(price_df,grade,location)
            if msg == "No matching location found": price = 0
        except: 
            price = 0
        pricing_df.loc["Basic Price", company] = price
        st.session_state.selected_group_df.at[idx, "Price Circular Date"] = price_circular_date
        # st.write(company, price)

        # FREIGHT
        freight = 0
        if (price_point == "Plant" and company in SPECIAL_FREIGHT_COMPANIES):
            try:
                (freight_df, freight_circular_date) = (read_data.read_freight_data_cached(
                        freight_sheet_name,price_date))
                freight = (get_freight(freight_df, delivery_location))
                if freight is None: 
                    freight = 0
                if freight_circular_date is not None:
                    st.session_state.selected_group_df.at[idx, "Freight Circular Date"] = freight_circular_date
            except:
                freight = 0
        pricing_df.loc["Freight", company] = freight
        

        # DISCOUNT
        for _, disc_row in discount_df.iterrows():

            disc_company = disc_row["company"]
            discount = disc_row["Discount"]

            qty_from = disc_row["Qty From"]
            qty_to = disc_row["Qty To"]
            amount = disc_row["Amount"]

            # Check quantity slab
            if not (qty_from <= selected_qty <= qty_to):
                continue

            # Create row if it doesn't exist
            if discount not in pricing_df.index:
                pricing_df.loc[discount] = 0
            else:
                # Apply to all companies
                if disc_company == "ALL":
                    pricing_df.loc[discount, :] = amount
                # Apply to a specific company
                elif disc_company in pricing_df.columns:
                    pricing_df.loc[discount,disc_company] = amount

    # 3. 🧼 EMPTY PROGRESS BAR ELEMENT ON LOOP COMPLETION
    progress_bar.empty()
    # Add Hidden Discount Row
    pricing_df.loc["Additi Discount", :] = 0.0
    # Rows to be deducted
    deduction_rows = [
        row for row in pricing_df.index
        if row not in ["Grade","Basic Price", "Freight"]
    ]

    pricing_df.loc["Net Price"] = (pricing_df.loc["Basic Price"]+ pricing_df.loc["Freight"]
                                        - pricing_df.loc[deduction_rows].sum())
    
    # st.write(pricing_df)
    # if "pricing_df" not in st.session_state:
    pricing_df.index.name = "Description"
    st.session_state.pricing_df = pricing_df.copy()

# MARKET INTELLIGENCE

# Helper Functions
def draw_line_charts(df, title="Trends Over Time"):
    # Dynamically get all columns except 'Date' as metrics
    metrics = [col for col in df.columns if col != "Date"]

    # Guard clause if there are no metric columns left to plot
    if not metrics:
        return None
    # Transform wide data to long format for Plotly Express
    df_melted = df.melt(id_vars=["Date"],value_vars=metrics,var_name="Metric",value_name="Value",)
    
    # Generate the chart
    fig = px.line(
        df_melted,
        x="Date",
        y="Value",
        color="Metric",
        title=title,
        template="plotly_white",
    )

    # Clean up aesthetics for Streamlit layout
    fig.update_layout(
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Value",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
        ),
    )
    fig.update_traces(connectgaps=True)
    return fig

def mi_table(df, chosen_metrics=""):
    # Get all columns that are NOT the Date column
    metric_cols = [col for col in df.columns if col != "Date"]


    if chosen_metrics == "":
        display_df = df.dropna().copy()
        display_df_formatted = display_df
    elif len(metric_cols) != 2:
        # Drop rows where ALL metric columns are NaN/None
        display_df = df.dropna(subset=metric_cols, how="all")

        # Replace any remaining isolated NaNs with '-' and format the Date nicely
        display_df_formatted = display_df.copy()
        display_df_formatted[metric_cols] = display_df_formatted[metric_cols].fillna("-")
    
    else:
        display_df = df.dropna().copy()
        display_df["Difference"] = display_df[metric_cols[0]] - display_df[metric_cols[1]]
        display_df_formatted = display_df
    
    display_df_formatted = display_df_formatted.sort_values(by="Date", ascending=False)
    # Format Date column to a cleaner string format (optional, e.g., DD/MM/YYYY)
    if pd.api.types.is_datetime64_any_dtype(display_df_formatted["Date"]):
        display_df_formatted["Date"] = display_df_formatted["Date"].dt.strftime("%d/%m/%Y")

    
    # st.write(display_df_formatted)
    render_excel_pivot(display_df_formatted,key=f"mi_table {np.random.randint(1, 1001)}")

# Historical Trend
def return_filtered_metric_df(df,mi_masters_df,date_from, date_to,chosen_metrics):

    if chosen_metrics == "Custom Metrics":
        chart_options = df.columns.drop("Date").tolist()
        selected_metrics = st.multiselect("Select Custom Metrics",chart_options,default=chart_options[14])
        
    else:
        match = mi_masters_df.loc[mi_masters_df["Metric Name"] == chosen_metrics,"Metrics"]

        if not match.empty:
            selected_metrics = [m.strip().strip('"').strip("'")
                                for m in match.iloc[0].split(",")]
        else:
            selected_metrics = []
    

    filtered_df = df.loc[
    (df["Date"] >= pd.to_datetime(date_from)) & (df["Date"] <= pd.to_datetime(date_to)),
                ["Date"] + selected_metrics]
    return filtered_df

# Moving Average Tab
def return_filtered_ma_df(df,date_from, date_to,chosen_metrics):
    df = df[["Date", chosen_metrics]].dropna().copy()
    df = df.sort_values("Date").set_index("Date")

    # Moving Averages
    df["MA 90"] = df[chosen_metrics].rolling("90D").mean()
    df["MA 180"] = df[chosen_metrics].rolling("180D").mean()
    df["MA 365"] = df[chosen_metrics].rolling("365D").mean()

    df = df.reset_index()
    filtered_df = df.loc[(df["Date"] >= pd.to_datetime(date_from)) & (df["Date"] <= pd.to_datetime(date_to))]
    
    return filtered_df

def moving_average_summary(plot_df, chosen_metrics):

    if plot_df.empty:
        st.warning("No data available for the selected period.")
        return

    latest = plot_df.iloc[-1]

    current = latest[chosen_metrics]
    ma90 = latest["MA 90"]
    ma180 = latest["MA 180"]
    ma365 = latest["MA 365"]

    # --------------------------------------------------------
    # Distance from Moving Averages
    # --------------------------------------------------------

    d90 = current - ma90
    d180 = current - ma180
    d365 = current - ma365

    p90 = d90 / ma90 * 100
    p180 = d180 / ma180 * 100
    p365 = d365 / ma365 * 100

    # --------------------------------------------------------
    # Trend Score (0-100)
    # --------------------------------------------------------

    score = 50

    # Position relative to MA
    score += 10 if current > ma90 else -10
    score += 15 if current > ma180 else -15
    score += 25 if current > ma365 else -25

    # Distance from MA365
    score += min(abs(p365), 20)

    if current < ma365:
        score -= min(abs(p365), 20)

    score = max(0, min(score, 100))

    # --------------------------------------------------------
    # Trend Classification
    # --------------------------------------------------------

    if score >= 85:
        condition = "🟢 Strong Bullish"

    elif score >= 70:
        condition = "🟢 Bullish"

    elif score >= 55:
        condition = "🟡 Mildly Bullish"

    elif score >= 45:
        condition = "🟡 Neutral"

    elif score >= 30:
        condition = "🟠 Mildly Bearish"

    elif score >= 15:
        condition = "🔴 Bearish"

    else:
        condition = "🔴 Strong Bearish"

    # --------------------------------------------------------
    # Executive Interpretation
    # --------------------------------------------------------

    if current > ma90 > ma180 > ma365:
        interpretation = (
            "The commodity is trading above all major moving averages, "
            "indicating a sustained upward trend across short-, medium- and "
            "long-term time horizons."
        )

    elif current < ma90 < ma180 < ma365:
        interpretation = (
            "The commodity is trading below all major moving averages, "
            "indicating persistent weakness and a well-established downward trend."
        )

    else:
        interpretation = (
            "The moving averages are not perfectly aligned, suggesting that "
            "the market is either consolidating or transitioning between trends."
        )

    with st.expander(":material/search_insights: Insights"):
        st.info(f"""
            **Market Condition:** **{condition}**

            **Trend Strength Score:** **{score:.0f}/100**

            {interpretation}

            The latest **{chosen_metrics}** price is **{current:.1f} USD/MT**.

            Compared with its historical trend:

            - **90-Day Average:** {ma90:.1f} USD/MT (**{abs(d90):.1f} USD/MT {'above' if d90>=0 else 'below'}**, {abs(p90):.1f}%)
            - **180-Day Average:** {ma180:.1f} USD/MT (**{abs(d180):.1f} USD/MT {'above' if d180>=0 else 'below'}**, {abs(p180):.1f}%)
            - **365-Day Average:** {ma365:.1f} USD/MT (**{abs(d365):.1f} USD/MT {'above' if d365>=0 else 'below'}**, {abs(p365):.1f}%)

            """)

# Correlation Analysis
def correlation_heatmap(df, title="Correlation Heatmap"):
    # Keep only numeric columns
    corr = df.select_dtypes(include="number").corr()

    fig = px.imshow(corr,text_auto=".2f",color_continuous_scale="RdBu_r",zmin=-1,zmax=1,
            aspect="auto",title=title,)

    fig.update_layout(height=600,margin=dict(l=20, r=20, t=60, b=20),
            coloraxis_colorbar=dict(title="Correlation"))
    fig.update_xaxes(side="bottom")

    return fig

# Price Driver Analysis
def price_driver_analysis(df, feedstocks, polymers, date_col="Date"):

    results = []

    working_df = df.copy()

    if date_col in working_df.columns:
        working_df = working_df.drop(columns=date_col)

    for feedstock in feedstocks:

        for polymer in polymers:

            temp = working_df[[feedstock, polymer]].dropna()

            if len(temp) < 20:
                continue

            X = temp[[feedstock]]
            y = temp[polymer]

            model = LinearRegression()
            model.fit(X, y)

            beta = model.coef_[0]
            intercept = model.intercept_
            r2 = model.score(X, y)
            corr = temp.corr().iloc[0, 1]

            results.append({
                "Feedstock": feedstock,
                "Polymer": polymer,
                "Impact of $10 Increase": round(beta * 10, 1),
                # "Beta ($/$)": round(beta, 2),
                "Correlation": round(corr, 3),
                "R²": round(r2, 3),
                # "Intercept": round(intercept, 1)
            })

    result_df = (pd.DataFrame(results))
    return result_df

# Relative Value Analysis
def spread_analysis(df, commodity, benchmark, lookback_years=3):

    # -------------------------
    # Prepare Data
    # -------------------------
    spread_df = (
        df[["Date", commodity, benchmark]]
        .dropna()
        .sort_values("Date")
        .copy()
    )

    spread_df["Spread"] = spread_df[commodity] - spread_df[benchmark]

    latest_date = spread_df["Date"].max()
    cutoff = latest_date - pd.DateOffset(years=lookback_years)

    stats_df = spread_df[spread_df["Date"] >= cutoff].copy()

    # Rolling moving averages (entire history for chart)
    spread_df = spread_df.set_index("Date")

    spread_df["MA 90"] = spread_df["Spread"].rolling("90D").mean()
    spread_df["MA 180"] = spread_df["Spread"].rolling("180D").mean()
    spread_df["MA 365"] = spread_df["Spread"].rolling("365D").mean()

    spread_df = spread_df.reset_index()

    # -------------------------
    # Statistics (Recent Regime)
    # -------------------------
    current = stats_df["Spread"].iloc[-1]
    average = stats_df["Spread"].mean()
    median = stats_df["Spread"].median()
    minimum = stats_df["Spread"].min()
    maximum = stats_df["Spread"].max()

    std = stats_df["Spread"].std()

    # z_score = 0 if std == 0 else (current - average) / std

    percentile = (
        stats_df["Spread"]
        .rank(pct=True)
        .iloc[-1] * 100
    )

    # Interpretation
    # if abs(z_score) < 1:
    #     z_text = "well within its normal trading range."
    # elif abs(z_score) < 2:
    #     z_text = "moderately away from its recent average, but still within the range of normal market fluctuations."
    # else:
    #     z_text = "at an unusually extreme level compared with the recent market regime."

    if percentile < 10:
        p_text = "among the lowest spreads observed."
    elif percentile < 25:
        p_text = "below its typical trading range."
    elif percentile <= 75:
        p_text = "within its normal historical range."
    elif percentile <= 90:
        p_text = "above its typical trading range."
    else:
        p_text = "among the highest spreads observed."

    with st.expander(":material/search_insights: Insights"):
        st.info(
            f"""
            The current spread between **{commodity}** and **{benchmark}** is **{current:.1f} USD/MT**.

            This analysis compares today's spread with the **last {lookback_years} years**, providing a view of the **current market regime** rather than the full historical record.

            - **Average Spread:** {average:.1f} USD/MT
            - **Median Spread:** {median:.1f} USD/MT
            - **Historical Range:** {minimum:.1f} to {maximum:.1f} USD/MT
            - **Current Percentile:** {percentile:.0f}th percentile ({p_text})

                """)

    # -------------------------
    # Spread Trend
    # -------------------------
    plot_df = spread_df.melt(
        id_vars="Date",
        value_vars=["Spread", "MA 90", "MA 180", "MA 365"],
        var_name="Series",
        value_name="Value"
    )

    fig = px.line(
        plot_df,
        x="Date",
        y="Value",
        color="Series",
        title=f"Spread Analysis: {commodity} vs {benchmark}"
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Spread (USD/MT)",
        hovermode="x unified",
        legend_title=""
    )

    st.plotly_chart(fig, width='stretch')

    # -------------------------
    # Distribution (Recent Regime)
    # -------------------------
    hist = px.histogram(
        stats_df,
        x="Spread",
        nbins=30,
        marginal="box",
        title=f"Spread Distribution (Last {lookback_years} Years)"
    )

    hist.update_layout(
        xaxis_title="Spread (USD/MT)",
        yaxis_title="Frequency"
    )

    st.plotly_chart(hist, width='stretch')

    return spread_df

# Market Dynamics
def return_market_dynamics_df(df, date_from, date_to, commodity):

    plot_df = df[["Date", commodity]].dropna().copy()

    plot_df["Date"] = pd.to_datetime(plot_df["Date"])

    plot_df = plot_df.sort_values("Date")

    # --------------------------
    # Daily Return (%)
    # --------------------------

    plot_df["Return"] = plot_df[commodity].pct_change() * 100

    # --------------------------
    # Rolling Volatility
    # --------------------------

    plot_df = plot_df.set_index("Date")

    plot_df["Volatility 30D"] = (
        plot_df["Return"]
        .rolling("30D")
        .std()
    )

    plot_df["Volatility 90D"] = (
        plot_df["Return"]
        .rolling("90D")
        .std()
    )

    plot_df = plot_df.reset_index()

    # =====================================================
    # Calendar based Rate of Change (ROC)
    # =====================================================

    def calculate_roc(days):

        current = plot_df[["Date", commodity]].rename(
            columns={
                "Date": "Current Date",
                commodity: "Current Price"
            }
        )

        history = plot_df[["Date", commodity]].rename(
            columns={
                "Date": "Past Date",
                commodity: "Past Price"
            }
        )

        current["Lookup Date"] = (
            current["Current Date"] -
            pd.Timedelta(days=days)
        )

        merged = pd.merge_asof(
            current.sort_values("Lookup Date"),
            history.sort_values("Past Date"),
            left_on="Lookup Date",
            right_on="Past Date",
            direction="backward"
        )

        return (
            (merged["Current Price"] /
             merged["Past Price"] - 1)
            * 100
        )

    plot_df["ROC 30D"] = calculate_roc(30)

    plot_df["ROC 90D"] = calculate_roc(90)

    # =====================================================
    # Acceleration
    # =====================================================

    roc = plot_df[["Date", "ROC 30D"]].copy()

    current = roc.rename(
        columns={
            "Date": "Current Date",
            "ROC 30D": "Current ROC"
        }
    )

    history = roc.rename(
        columns={
            "Date": "Past Date",
            "ROC 30D": "Past ROC"
        }
    )

    current["Lookup Date"] = (
        current["Current Date"] -
        pd.Timedelta(days=30)
    )

    merged = pd.merge_asof(
        current.sort_values("Lookup Date"),
        history.sort_values("Past Date"),
        left_on="Lookup Date",
        right_on="Past Date",
        direction="backward"
    )

    plot_df["Acceleration"] = (
        merged["Current ROC"] -
        merged["Past ROC"]
    )

    # --------------------------

    plot_df = plot_df.loc[
        (plot_df["Date"] >= pd.to_datetime(date_from)) &
        (plot_df["Date"] <= pd.to_datetime(date_to))
    ]

    return plot_df

def market_dynamics_summary(plot_df, commodity):

    latest = plot_df.iloc[-1]

    current_price = latest[commodity]

    vol = latest["Volatility 30D"]

    roc = latest["ROC 30D"]

    acceleration = latest["Acceleration"]

    avg_vol = plot_df["Volatility 30D"].mean()

    percentile = (
        plot_df["Volatility 30D"]
        .rank(pct=True)
        .iloc[-1] * 100
    )

    # --------------------------------
    # Volatility Regime
    # --------------------------------

    if percentile < 20:
        regime = "Very Stable"
        stability = 90

    elif percentile < 40:
        regime = "Stable"
        stability = 75

    elif percentile < 60:
        regime = "Normal"
        stability = 60

    elif percentile < 80:
        regime = "Elevated"
        stability = 40

    else:
        regime = "Highly Volatile"
        stability = 20

    # --------------------------------
    # Trend
    # --------------------------------

    if roc > 5:
        trend = "Strong Bullish"

    elif roc > 2:
        trend = "Bullish"

    elif roc > -2:
        trend = "Neutral"

    elif roc > -5:
        trend = "Bearish"

    else:
        trend = "Strong Bearish"

    # --------------------------------
    # Momentum
    # --------------------------------

    if acceleration > 2:
        accel = "Strengthening"

    elif acceleration < -2:
        accel = "Weakening"

    else:
        accel = "Stable"

    # --------------------------------
    # Market Dynamics Score
    # --------------------------------

    trend_score = min(max(roc + 50, 0), 100)

    dynamics = (
        trend_score * 0.45 +
        stability * 0.35 +
        (50 + acceleration * 5) * 0.20
    )

    dynamics = max(0, min(100, dynamics))

    with st.expander(":material/search_insights: Insights"):
        st.info(f"""

            ### Overall Market Dynamics : **{dynamics:.0f}/100**

            **Trend:** {trend}

            **Volatility Regime:** {regime}

            **Momentum:** {accel}

            The latest **{commodity}** price is **{current_price:.1f} USD/MT**.

            The commodity has generated a **30-Day Rate of Change (ROC)** of **{roc:.2f}%**, indicating the overall direction and strength of the recent price movement.

            Current **30-Day Volatility** is **{vol:.2f}%**, compared with a historical average of **{avg_vol:.2f}%**. This places current market volatility in the **{percentile:.0f}th percentile** of the selected period.

            The **Acceleration** indicator is **{accel.lower()}**, suggesting that the rate of price movement is {'increasing' if acceleration > 0 else 'decreasing'}.

            Overall, the market is characterized by a **{trend.lower()} trend**, **{regime.lower()} market conditions**, and **{accel.lower()} momentum**.
            """)
    
def draw_market_dynamics(plot_df):

    # ==========================
    # Volatility Chart
    # ==========================

    fig_vol = px.line(
        plot_df,
        x="Date",
        y=["Volatility 30D", "Volatility 90D"],
        title="Rolling Volatility"
    )

    fig_vol.update_layout(
        height=450,
        hovermode="x unified",
        legend_title="",
        xaxis_title="",
        yaxis_title="Volatility (%)"
    )

    # ==========================
    # Momentum & Acceleration
    # ==========================

    fig_mom = px.line(
        plot_df,
        x="Date",
        y=["ROC 30D", "ROC 90D", "Acceleration"],
        title="Market Momentum"
    )

    fig_mom.update_layout(
        height=450,
        hovermode="x unified",
        legend_title="",
        xaxis_title="",
        yaxis_title="ROC / Acceleration (%)"
    )

    return fig_vol, fig_mom

# Seasonality Tab
def return_seasonality_df(df, commodity):

    plot_df = df[["Date", commodity]].dropna().copy()

    plot_df["Date"] = pd.to_datetime(plot_df["Date"])

    plot_df = plot_df.sort_values("Date")

    # Month-end price
    monthly = (plot_df.set_index("Date").resample("ME").last().reset_index())

    # Monthly Return
    monthly["Monthly Return"] = (monthly[commodity].pct_change() * 100)
    monthly["Year"] = monthly["Date"].dt.year
    monthly["Month"] = monthly["Date"].dt.month_name().str[:3]
    month_order = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    monthly["Month"] = pd.Categorical(monthly["Month"],categories=month_order,ordered=True)

    # Summary Statistics

    seasonality = (
        monthly
        .groupby("Month", observed=False)
        .agg(
            Average_Return=("Monthly Return","mean"),
            Median_Return=("Monthly Return","median"),
            Volatility=("Monthly Return","std"),
            Positive_Months=("Monthly Return", lambda x: (x>0).sum()),
            Observations=("Monthly Return","count")
        )
        .reset_index()
    )

    # Heatmap Data
    heatmap = monthly.pivot_table(index="Year",columns="Month",values="Monthly Return")

    return monthly, seasonality, heatmap

def seasonality_summary(seasonality):

    best = seasonality.loc[seasonality["Average_Return"].idxmax()]
    worst = seasonality.loc[seasonality["Average_Return"].idxmin()]
    volatile = seasonality.loc[seasonality["Volatility"].idxmax()]
    consistent = seasonality.loc[(seasonality["Positive_Months"] / seasonality["Observations"]).idxmax()]

    with st.expander(":material/search_insights: Insights"):
        st.info(f"""
            Historically, **{best['Month']}** has been the strongest month, delivering an average return of **{best['Average_Return']:.2f}%**.

            Conversely, **{worst['Month']}** has produced the weakest average performance with an average return of **{worst['Average_Return']:.2f}%**.

            **{volatile['Month']}** exhibits the highest month-to-month volatility, indicating greater uncertainty during this period.

            The most consistently positive month has been **{consistent['Month']}**, where prices increased in **{consistent['Positive_Months']} out of {consistent['Observations']}** years.

            """)
    
def draw_seasonality(seasonality, heatmap):

    # Average Monthly Return

    fig_return = px.bar(seasonality,x="Month",y="Average_Return",title="Average Monthly Return")
    fig_return.update_layout(xaxis_title="",yaxis_title="Average Return (%)")

    # Monthly Volatility
    fig_vol = px.bar(seasonality, x="Month", y="Volatility",title="Monthly Volatility")
    fig_vol.update_layout(xaxis_title="",yaxis_title="Volatility (%)")

    # Heatmap
    fig_heat = px.imshow(heatmap,aspect="auto",color_continuous_scale="RdYlGn",title="Monthly Return Heatmap")
    fig_heat.update_layout(xaxis_title="Month",yaxis_title="Year")

    return fig_return, fig_vol, fig_heat

# Margin Page - Calculation
def return_filtered_margin_df(df, date_from, date_to, selected_margin_on, selected_metrics):
    filtered_df = (df.loc[
    (df["Date"] >= pd.to_datetime(date_from)) & (df["Date"] <= pd.to_datetime(date_to)),
                ["Date", selected_margin_on] + selected_metrics]).dropna().copy()
    
    # Create a separate DataFrame for the differences
    margin_df = pd.DataFrame()
    margin_df["Date"] = filtered_df["Date"]

    # Direct vector subtraction for each selected metric
    for metric in selected_metrics:
        margin_df[f"Margin {metric}"] = (filtered_df[metric] - filtered_df[selected_margin_on])
    
    # Merge the raw data and difference data on the Date column
    combined_df = pd.merge(filtered_df, margin_df, on="Date", how="inner")

    return filtered_df,margin_df, combined_df

# Tab Executive Summary
def executive_summary(df, date_from, date_to, commodity):
    ma_df = return_filtered_ma_df(df, date_from, date_to, commodity)
    md_df = return_market_dynamics_df(df, date_from, date_to, commodity)
    monthly_df, seasonality_df, heatmap_df = return_seasonality_df(df,commodity)
    
    # Date
    summary_date = ma_df["Date"].max()

    # Latest Moving Average
    latest_ma = ma_df.iloc[-1]
    latest_md = md_df.iloc[-1]

    # market dynamics
    current_price = latest_ma[commodity]
    ma90 = latest_ma["MA 90"]
    ma365 = latest_ma["MA 365"]
    roc = latest_md["ROC 30D"]
    vol = latest_md["Volatility 30D"]
    acc = latest_md["Acceleration"]

    if current_price > ma90 > ma365:
        trend = "Bullish"
    elif current_price < ma90 < ma365:
        trend = "Bearish"
    else:
        trend = "Neutral"
    
    if acc > 2:
        momentum = "Strengthening"
    elif acc < -2:
        momentum = "Weakening"
    else:
        momentum = "Stable"
    
    avg_vol = md_df["Volatility 30D"].mean()

    if vol > avg_vol*1.5:
        regime = "Highly Volatile"
    elif vol > avg_vol:
        regime = "Elevated"
    else:
        regime = "Stable"
    
    today = datetime.today().strftime("%b")
    month = seasonality_df.loc[seasonality_df["Month"] == today]
    seasonality = "Positive"
    if len(month):
        if month.iloc[0]["Average_Return"] < 0:
            seasonality = "Negative"

    metrics = [
        ("Data As Of", summary_date.strftime("%d %b %Y")),
        ("Current Price", f"{current_price:.2f}"),
        ("Trend", trend),
        ("Momentum", momentum),
        ("Volatility", regime),
        ("Seasonality", seasonality),
        # ("ROC (30D)", f"{roc:.2f}%"),
        # ("Acceleration", f"{acc:.2f}%"),
        # ("MA 90", f"{ma90:.2f}"),
        # ("MA 365", f"{ma365:.2f}")
    ]

    for i in range(0, len(metrics), 3):
        cols = st.columns(3)

        for col, (label, value) in zip(cols, metrics[i:i+3]):
            with col:
                st.metric(label, value)
    

    st.info(f"""
        ### Executive Summary

        **{commodity}** is currently in a **{trend.lower()}** market.

        Momentum is **{momentum.lower()}**, while market volatility is **{regime.lower()}**.

        Historical seasonality for the current month is **{seasonality.lower()}**.

        The latest price is **{current_price:.1f} USD/MT**, with a 30-Day Rate of Change(ROC) of **{roc:.2f}%**.

        Overall, current market conditions suggest a **{trend.lower()} trend with {momentum.lower()} momentum**, while volatility should continue to be monitored.
        """)
