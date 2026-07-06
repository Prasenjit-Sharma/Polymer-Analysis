from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
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
            use_container_width=True,
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
        st.error(f"TradingView connection error: {e}")
        return None

def display_market_metrics():
    # Fetch metrics globally
    with st.container(border=True):
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
SPECIAL_FREIGHT_COMPANIES = ["HMEL", "OPAL", "HPL", "NAYARA","MRPL"]

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

# CREATE FORM

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
    st.session_state.pricing_df = pricing_df.copy()

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
            df_actions(st.session_state.pricing_df,index=True)
        with col2:
            is_view_group = st.toggle("View Pricing Group")
                
        if is_view_group: 
            st.dataframe(st.session_state.selected_group_df,width="stretch",hide_index=True)
        
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
            

