from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import pandas as pd
import plotly.express as px
from io import BytesIO
import streamlit as st
from mitosheet.streamlit.v1 import spreadsheet
import requests
from bs4 import BeautifulSoup


FISCAL_START = 4

month_order = ["April", "May", "June", 
               "July", "August", "September", "October", "November", "December","January", "February", "March"]

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

def draw_histogram_month_quantity(df, color = None, title=None):
    # Get only months that exist in the data, in the correct order
    months_in_data = [m for m in month_order if m in df['Month Name'].unique()]
    fig = px.histogram(
            df.sort_values(by='Month Name'),
            x="Month Name",
            y="Quantity",
            # pattern_shape="Material Group",
            color=color,
            title=title,
            # barmode="group", # Groups the bars side-by-side
            category_orders={"Month Name": months_in_data},
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
    fig = px.histogram(df, x=x, y=y,
                    color=color, barmode='group',text_auto=True)
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5),
        xaxis_title="",
        yaxis_title="",
        margin=dict(l=50, r=50, t=80, b=100)  # Adjust left margin
    )
    return fig

def download_excel(df, filename='data.xlsx', button_label='📥 Download Excel', key='download_button'):
    """
    Create a download button for formatted Excel file in Streamlit
    """
    buffer = BytesIO()
    
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        
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

def df_actions(df, filename='data.xlsx', key='df_actions'):
    col1, col2 = st.columns(2)
    
    with col1:
        # Download button
        st.download_button(
            label="📥 Download Excel",
            data=download_excel(df, filename),
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

def apply_common_styles(title):
    st.set_page_config(layout="wide") 
    st.markdown(f"### {title}")
    st.markdown("""
        <style>
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 3rem !important;
        }
        </style>
    """, unsafe_allow_html=True)

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