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
        spreadsheet_url = "https://docs.google.com/spreadsheets/d/18sGa7-DQ0v0oHpMesTySUjr9Z4dh70hr4PUNm6t3uo0/"
        worksheet_name = "RawSales"
        df = read_data.read_gsheet(spreadsheet_url, worksheet_name)

        #Data Cleaning
        # Convert Net Billing with commas to Float
        df["Net Value of Billing item"] = (
            df["Net Value of Billing item"]
            .str.replace(",", "")
            .astype("Float64")  # nullable integer
        )
        # Convert Date to Datetime
        df["Billing Date"] = pd.to_datetime(df["Billing Date"])

        # Replace part of string - Material Description
        df["Material Description"] = df["Material Description"].apply(lambda x: x.replace("HP DURAPOL ", ""))
        df["Material Description"] = df["Material Description"].apply(lambda x: x.replace("-MS", ""))
        return df
