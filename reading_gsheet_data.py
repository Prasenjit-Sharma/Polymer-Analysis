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
        
        # Keeping Customer ID as string
        df["Sold-to Party"] = df["Sold-to Party"].astype(str)

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
