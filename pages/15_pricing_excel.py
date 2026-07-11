import streamlit as st
import utilities
from reading_gsheet_data import read_data
from datetime import date

utilities.apply_common_styles("Pricing Circular")

# 3. Data Downloader & Grid Viewer Sandbox (Isolated Fragment)
@st.fragment
def render_data_viewer():
    if "selected_sheet" in st.session_state and "selected_url" in st.session_state:
        file_name = st.session_state["filename"]
        spreadsheet_url = st.session_state["selected_url"]
        selected_sheet = st.session_state["selected_sheet"]
        active_company = st.session_state.get("active_company", "Data")
        download_file_name = f"{file_name}_{selected_sheet}.xlsx"

        st.write("---")
        # Add a helpful subtle indicator showing what sheet is currently loaded
        st.subheader(f"Price Circular: {file_name} - {selected_sheet}")
        
        try:
            df = read_data.read_gsheet(spreadsheet_url, selected_sheet)
            st.dataframe(df, width="stretch",hide_index=True,)
            utilities.df_actions(df, filename=download_file_name, index=False)
            
        except Exception as e:
            st.error(f"Failed to read sheet data: {e}")

# Initialize tracking flags if they aren't in session state yet
if "show_circulars" not in st.session_state:
    st.session_state["show_circulars"] = False

# Initialize tracking flags if they aren't in session state yet
if "filename" not in st.session_state:
    st.session_state["filename"] = ""

# 1. Main Search Filters Input Row
with st.container(border=True):
    # Calculate today and the start of the current month dynamically
    today = date.today()
    start_of_month = today.replace(day=1)
    col1, col2, col3, col4 = st.columns(4, vertical_alignment="bottom")
    with col1:
        date_from = st.date_input("From Date", format="DD/MM/YYYY", value=start_of_month)
    with col2:
        date_to = st.date_input("To Date", format="DD/MM/YYYY", value=today)
    with col3:
        company = st.selectbox("Company", utilities.COMPANIES)
    with col4:
        if st.button("Fetch Circulars", type="primary", width="stretch"):
            st.session_state["show_circulars"] = True
            st.session_state["active_company"] = company
            # CRITICAL: Store filter boundaries to use during loop evaluation
            st.session_state["filter_date_from"] = date_from
            st.session_state["filter_date_to"] = date_to

            # Clear previous sheet selections
            st.session_state.pop("selected_sheet", None)
            st.session_state.pop("selected_url", None)
            st.rerun()

# 2. Circular Matrix Grid (Filtered dynamically by date boundaries)
if st.session_state["show_circulars"]:
    target_company = st.session_state["active_company"]
    f_from = st.session_state["filter_date_from"]
    f_to = st.session_state["filter_date_to"]

    pricing_secrets = st.secrets.get("pricing", {})
    company_files = {
        key: value
        for key, value in pricing_secrets.items()
        if key.startswith(target_company)
    }
    total_rows = len(company_files)
    progress_text = "Fetching pricing matrix structures. Please wait..."
    progress_bar = st.progress(0, text=progress_text)

    no_of_cols = 6
    for idx, (file_name, spreadsheet_url) in enumerate(company_files.items()):
    # for file_name, spreadsheet_url in company_files.items():
        # 2. UPDATE PROGRESS PERCENTAGE DYNAMICALLY
        current_percentage = int(((idx + 1) / total_rows) * 100)
        progress_bar.progress(current_percentage, text=f"{progress_text} ({current_percentage}%)")

        spreadsheet, sheet_names = read_data.get_sheet_names_cached(spreadsheet_url)

        # Apply the date range filtering logic here
        filtered_sheets = []
        for name in sheet_names:
            sheet_date = utilities.parse_sheet_date(name)
            if sheet_date is not None:
                # Keep the sheet if it falls within the requested boundary range
                if f_from <= sheet_date <= f_to:
                    filtered_sheets.append(name)
            else:
                # Optional fallback: always display non-date sheets
                filtered_sheets.append(name)

        # Only draw the expander if there are matching sheets within the range
        if filtered_sheets:
            with st.expander(file_name, expanded=True):
                sheet_cols = st.columns(no_of_cols)

                for idx, name in enumerate(filtered_sheets):
                    col_idx = idx % no_of_cols

                    with sheet_cols[col_idx]:
                        button_key = f"btn_{file_name}_{name}_{idx}"

                        if st.button(
                            name, key=button_key, width="stretch"
                        ):
                            st.session_state["filename"] = file_name
                            st.session_state["selected_sheet"] = name
                            st.session_state["selected_url"] = spreadsheet_url
                            st.session_state["show_circulars"] = False
                            st.rerun()
        else:
            st.caption(
                f"ℹ️ {file_name}: No circulars found matching the selected date range."
            )
    
    progress_bar.empty()
# Run the isolated visual window component 
render_data_viewer()
