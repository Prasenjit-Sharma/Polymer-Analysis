import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

class read_data():
    
    @staticmethod
    def read_gsheet(spreadsheet_url: str, worksheet_name: str):
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn.read(
            spreadsheet=spreadsheet_url,
            worksheet=worksheet_name,
            usecols=None
        )
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def fetch_sales_data():
        spreadsheet_url = st.secrets["file_address"]["SPREADSHEET_URL"]
        worksheet_name = st.secrets["file_address"]["WORKSHEET_SALES"]
        df = read_data.read_gsheet(spreadsheet_url, worksheet_name)
        
        #Data Cleaning
        #Remove Blank Rows and Columns
        df = df.dropna(subset=["Billing Date"])
        df = df.loc[:, ~df.columns.str.contains("Unnamed")]


        # Convert Net Billing with commas to Float
        df["Net Value of Billing item"] = (
            df["Net Value of Billing item"]
            .str.replace(",", "")
            .astype("Float64")  # nullable integer
        )
        
        # Convert Date to Datetime
        df["Billing Date"] = pd.to_datetime(df["Billing Date"],dayfirst=True, format="mixed")
        df["Year"] = df["Billing Date"].dt.year
        df["Month"] = df["Billing Date"].dt.month
        df['Month Name'] = df['Billing Date'].dt.month_name()

        # Keeping Customer ID as string
        df["Sold-to Party"] = df["Sold-to Party"].astype(str)
        # df["Ship-to Party"] = df["Ship-to Party"].astype(str)
        # df["Billing Document No."] = df["Billing Document No."].astype(str)
        # df["Material"] = df["Material"].astype(str)
        # df["Plant"] = df["Plant"].astype(str)
        # df["Fiscal Year"] = df["Fiscal Year"].astype(str)
        # df["Year"] = df["Year"].astype(str)
        # df["Month"] = df["Month"].astype(str)
        
        # Replace part of string - Material Description
        df["Material Description"] = df["Material Description"].apply(lambda x: x.replace("HP DURAPOL ", ""))
        df["Material Description"] = df["Material Description"].apply(lambda x: x.replace("-MS", ""))
        
        # Call Function Fetch CMR Data
        df_cmr = read_data.fetch_cmr_data()
        df = df.merge(df_cmr[["Ship-to Party", "Regional Office"]],on="Ship-to Party",how="left")
        df["Regional Office"] = df["Regional Office"].fillna("Unknown")
        

        # Call Function Customer Group
        df_group = read_data.fetch_group_data()
        df = df.merge(df_group[["Sold-to Party", "Sold-to Group"]],on="Sold-to Party",how="left")
        df["Sold-to Group"] = df["Sold-to Group"].fillna(df["Sold-to-Party Name"])

        # Material Family (PP/PE)
        material_family_map = {
            "PP": "PP",
            "LLDPE": "PE",
            "HDPE": "PE"
        }

        df["Material Family"] = df["Material Group"].map(material_family_map)

        return df
    
    def fetch_cmr_data():
        spreadsheet_url = st.secrets["file_address"]["SPREADSHEET_URL"]
        worksheet_name = st.secrets["file_address"]["WORKSHEET_CMR"]
        df = read_data.read_gsheet(spreadsheet_url, worksheet_name)
        # Keeping Customer ID as string
        df["Sold-to Party"] = df["Sold-to Party"].astype(str)

        return df
    
    def fetch_group_data():
        spreadsheet_url = st.secrets["file_address"]["SPREADSHEET_URL"]
        worksheet_name = st.secrets["file_address"]["WORKSHEET_GROUP"]
        df = read_data.read_gsheet(spreadsheet_url, worksheet_name)

        # Keeping Customer ID as string
        df["Sold-to Party"] = df["Sold-to Party"].astype(str)

        return df
    
    def fetch_mou_data():
        spreadsheet_url = st.secrets["file_address"]["SPREADSHEET_URL"]
        worksheet_name = st.secrets["file_address"]["WORKSHEET_MOU"]
        df = read_data.read_gsheet(spreadsheet_url, worksheet_name)
        # Blank cells as 0
        df["PP"] = df["PP"].fillna(0)
        df["PE"] = df["PE"].fillna(0)
        # Keeping Customer ID as string
        df["Sold-to Party"] = df["Sold-to Party"].astype(str)
        # Date Correction
        df["MOU Start Date"] = pd.to_datetime(df["MOU Start Date"])
        df["MOU End Date"] = pd.to_datetime(df["MOU End Date"])
        # Call Function Customer Group
        df_group = read_data.fetch_group_data()
        df = df.merge(df_group[["Sold-to Party", "Sold-to Group"]],on="Sold-to Party",how="left")
        df["Sold-to Group"] = df["Sold-to Group"].fillna(df["Sold-to-Party Name"])
        # Rename specific columns
        # df = df.rename(columns={"PP": "MOU PP", "PE": "MOU PE"})
        return df

    @staticmethod
    @st.cache_data(ttl=3600)
    def inventory_ahmd_data():
        spreadsheet_url = st.secrets["file_address"]["INVENTORY_SHEET_URL"]
        worksheet_name = st.secrets["file_address"]["WORKSHEET_AHMD_INVENTORY"]
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(
            spreadsheet=spreadsheet_url,
            worksheet=worksheet_name,
            usecols = None,
            header = [0,1]
        )
        
        return df
    
    # Pricing Sheets
    
    def get_sheet_names(spreadsheet_url):
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(
            st.secrets["connections"]["gsheets"],
            scopes=scopes
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_url(spreadsheet_url)
        sheet_titles = [ws.title for ws in spreadsheet.worksheets()]
        return spreadsheet, sheet_titles
    
    @st.cache_data(ttl=3600)
    def get_sheet_names_cached(spreadsheet_url):

        return read_data.get_sheet_names(
            spreadsheet_url)
    
    def get_nearest_lower_date(sheet_names, input_date):
        # Convert only if string
        if isinstance(input_date, str):
            input_date = datetime.strptime(input_date, "%d.%m.%Y").date()

        valid_dates = []

        for sheet in sheet_names:
            try:
                sheet_date = datetime.strptime(sheet, "%d.%m.%Y").date()

                if sheet_date <= input_date:
                    valid_dates.append(sheet_date)

            except ValueError:
                pass

        if not valid_dates:
            return None

        nearest_date = max(valid_dates)

        return nearest_date.strftime("%d.%m.%Y")

    @staticmethod
    def read_pricing_data(spreadsheet_name, price_date):
        spreadsheet_url = st.secrets["pricing"][spreadsheet_name]
        spreadsheet, sheet_names = read_data.get_sheet_names(spreadsheet_url)
        worksheet_name = read_data.get_nearest_lower_date(sheet_names,price_date)
        df = read_data.read_gsheet(spreadsheet_url, worksheet_name)
        return df, worksheet_name

    @st.cache_data(ttl=3600)
    def read_pricing_data_cached(spreadsheet_name,price_date):

        return read_data.read_pricing_data(
            spreadsheet_name,price_date)

    def read_freight_data(freight_sheet_name,price_date):
        spreadsheet_url = st.secrets["pricing"][freight_sheet_name]
        spreadsheet, sheet_names = read_data.get_sheet_names(spreadsheet_url)
        worksheet_name = read_data.get_nearest_lower_date(sheet_names,price_date)
        df = read_data.read_gsheet(spreadsheet_url, worksheet_name)
        return df, worksheet_name

    @st.cache_data(ttl=3600)
    def read_freight_data_cached(freight_sheet_name,price_date):
        return read_data.read_freight_data(freight_sheet_name,price_date)
     
    @st.cache_data(ttl=300)
    def read_groups_data(spreadsheet_url):

        spreadsheet, sheet_names = read_data.get_sheet_names(
            spreadsheet_url
        )

        worksheet = spreadsheet.worksheet("Groups")

        return pd.DataFrame(
            worksheet.get_all_records()
        )

    @st.cache_data(ttl=3600)
    def read_discount_data(spreadsheet_url,family):
        # spreadsheet_url = st.secrets["pricing"]["PUBLISHED_DISCOUNT_MASTER_SHEET"]
        df = read_data.read_gsheet(spreadsheet_url,family)
        df["Date From"] = pd.to_datetime(df["Date From"],format="mixed").dt.date
        df["Date To"] = pd.to_datetime(df["Date To"],format="mixed").dt.date
        return df


