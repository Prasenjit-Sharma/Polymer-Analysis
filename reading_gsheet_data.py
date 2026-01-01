import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

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
    @st.cache_data
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

        # Replace part of string - Material Description
        df["Material Description"] = df["Material Description"].apply(lambda x: x.replace("HP DURAPOL ", ""))
        df["Material Description"] = df["Material Description"].apply(lambda x: x.replace("-MS", ""))
        
        # Call Function Fetch CMR Data
        df_cmr = read_data.fetch_cmr_data()
        df = df.merge(df_cmr[["Sold-to Party", "Regional Office"]],on="Sold-to Party",how="left")
        df["Regional Office"] = df["Regional Office"].fillna("Unknown")
        
        return df
    
    def fetch_cmr_data():
        spreadsheet_url = st.secrets["file_address"]["SPREADSHEET_URL"]
        worksheet_name = st.secrets["file_address"]["WORKSHEET_CMR"]
        df = read_data.read_gsheet(spreadsheet_url, worksheet_name)

        return df
    
