from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
import json
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.http import MediaInMemoryUpload
import streamlit as st
import pandas as pd
from calendar import monthrange
from st_aggrid import AgGrid, GridOptionsBuilder

class discount():

    # Connect to Google drive for JSON
    def get_drive_service():
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["connections"]["gsheets"],
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build("drive", "v3", credentials=creds)
    
    # Read Google JSON Discount file
    @staticmethod
    def read_json_from_drive():
        file_id = st.secrets["file_address"]["JSON_FILE_ID"]
        drive_service = discount.get_drive_service()

        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        fh.seek(0)
        return json.load(fh)
    
    # Append existing JSON to new discount entry
    @staticmethod
    def append_discount(existing_json: dict, discount_payload: dict):
        # Defensive conversion
        if isinstance(discount_payload, str):
            discount_payload = json.loads(discount_payload)

        if not isinstance(discount_payload, dict):
            raise TypeError("discount_payload must be a dict")

        discount_type = discount_payload["discount_type"]

        # remove control key
        record = discount_payload.copy()
        record.pop("discount_type")

        # ensure list exists
        if discount_type not in existing_json:
            existing_json[discount_type] = []

        # optional: check overlapping dates
        existing_json[discount_type].append(record)

        return existing_json
    
    # Write Google JSON Discount file
    @staticmethod
    def overwrite_json_in_drive(data):
        file_id = st.secrets["file_address"]["JSON_FILE_ID"]
        drive_service = discount.get_drive_service()

        json_bytes = json.dumps(data, indent=2).encode("utf-8")

        media = MediaInMemoryUpload(
            json_bytes,
            mimetype="application/json",
            resumable=False
        )

        drive_service.files().update(
            fileId=file_id,
            media_body=media
        ).execute()

    @staticmethod
    def apply_discount(filtered_df: pd.DataFrame, monthly_discounts: dict):
        df = filtered_df.copy()
        df["Total Credit Note"] = 0.0
        df["Total Discount"] = 0.0

        # if "Cash Discount" in monthly_discounts:
          
        #     discounts = monthly_discounts["Cash Discount"]
        #     for disc in discounts:
        #         discount_amount = disc.get("discount_amount", 0.0)
        #         material_groups = disc.get("material_groups", [])

        #         # Normalize material groups (safety)
        #         if isinstance(material_groups, str):
        #             material_groups = [material_groups]

        #         # Parse discount validity dates
        #         disc_start = pd.to_datetime(disc["start_date"])
        #         disc_end = pd.to_datetime(disc["end_date"])

        #         # Build combined eligibility mask
        #         mask = (
        #             df["Material Group"].isin(material_groups) &
        #             (df["Billing Date"] >= disc_start) &
        #             (df["Billing Date"] <= disc_end)
        #         )
        #         df.loc[mask, "Cash Discount"] = (
        #             discount_amount
        #         )
        #         df.loc[mask, "Cash Discount Amount"] = (
        #             df.loc[mask, "Quantity"] * discount_amount
        #         )
        #         df["Total Credit Note"] += df["Cash Discount Amount"]
        #         df["Total Discount"] += df["Cash Discount Amount"]

        if "MOU Discount" in monthly_discounts:
            
            discounts = monthly_discounts["MOU Discount"]
            for disc in discounts:
                month_discount_amount = disc.get("monthly_component", 0.0)
                annual_discount_amount = disc.get("annual_component", 0.0)
                material_groups = disc.get("material_groups", [])

                # Normalize material groups (safety)
                if isinstance(material_groups, str):
                    material_groups = [material_groups]

                disc_start = pd.to_datetime(disc["start_date"])
                disc_end = pd.to_datetime(disc["end_date"])

                # Build combined eligibility mask
                mask = (
                    df["Material Group"].isin(material_groups) &
                    (df["Billing Date"] >= disc_start) &
                    (df["Billing Date"] <= disc_end)
                )
                df.loc[mask, "Month MOU Discount"] = (
                    month_discount_amount
                )
                df.loc[mask, "Month MOU Discount Amount"] = (
                    df.loc[mask, "Quantity"] * month_discount_amount
                )
                df.loc[mask, "Annual MOU Discount"] = (
                    month_discount_amount
                )
                df.loc[mask, "Annual MOU Discount Amount"] = (
                    df.loc[mask, "Quantity"] * month_discount_amount
                )
                df["Total Credit Note"] += df["Month MOU Discount Amount"]
                df["Total Discount"] += df["Month MOU Discount Amount"] + df["Annual MOU Discount Amount"]
        
        if "Early Bird" in monthly_discounts:
            
            discounts = monthly_discounts["Early Bird Discount"]
            for disc in discounts:
                discount_amount = disc.get("discount_amount", 0.0)
                material_groups = disc.get("material_groups", [])

                # Normalize material groups (safety)
                if isinstance(material_groups, str):
                    material_groups = [material_groups]

                disc_start = pd.to_datetime(disc["start_date"])
                disc_end = pd.to_datetime(disc["end_date"])

                # Build combined eligibility mask
                mask = (
                    df["Material Group"].isin(material_groups) &
                    (df["Billing Date"] >= disc_start) &
                    (df["Billing Date"] <= disc_end)
                )

                df.loc[mask, "Early Bird Discount"] = (
                    discount_amount
                )
                df.loc[mask, "Early Bird Amount"] = (
                    df.loc[mask, "Quantity"] * discount_amount
                )
                df["Total Credit Note"] += df["Early Bird Amount"]
                df["Total Discount"] += df["Early Bird Amount"]

        if "Price Protection" in monthly_discounts:
            
            discounts = monthly_discounts["Price Protection Discount"]
            for disc in discounts:
                discount_amount = disc.get("discount_amount", 0.0)
                material_groups = disc.get("material_groups", [])

                # Normalize material groups (safety)
                if isinstance(material_groups, str):
                    material_groups = [material_groups]

                disc_start = pd.to_datetime(disc["start_date"])
                disc_end = pd.to_datetime(disc["end_date"])

                # Build combined eligibility mask
                mask = (
                    df["Material Group"].isin(material_groups) &
                    (df["Billing Date"] >= disc_start) &
                    (df["Billing Date"] <= disc_end)
                )

                df.loc[mask, "Price Protection"] = (
                    discount_amount
                )
                df.loc[mask, "Price Protection Amount"] = (
                    df.loc[mask, "Quantity"] * discount_amount
                )
                df["Total Credit Note"] += df["Price Protection Amount"]
                df["Total Discount"] += df["Price Protection Amount"]
        
        if "Freight Discount" in monthly_discounts:
            
            discounts = monthly_discounts["Freight Discount"]
            cmr_df = st.session_state["CMR Data"]
            # Merge distance into sales
            df = df.merge(
                cmr_df[["Ship-to Party", "Warehouse Distance"]],
                on="Ship-to Party",
                how="left"
            )

            if df["Warehouse Distance"].isna().any():
                missing = df[df["Warehouse Distance"].isna()]["Ship-to Party"].unique()
                raise ValueError(f"Missing distance for Ship-to Party: {missing}")
            
            for disc in discounts:
                less_dist_value = disc.get("less_dist_value", 0.0)
                high_dist_value = disc.get("high_dist_value", 0.0)
                material_groups = disc.get("material_groups", [])

                # Normalize material groups (safety)
                if isinstance(material_groups, str):
                    material_groups = [material_groups]

                disc_start = pd.to_datetime(disc["start_date"])
                disc_end = pd.to_datetime(disc["end_date"])

                # Build combined eligibility mask
                mask = (
                    df["Material Group"].isin(material_groups) &
                    (df["Billing Date"] >= disc_start) &
                    (df["Billing Date"] <= disc_end)
                )

                df.loc[mask, "Freight Discount"] = df.loc[mask, "Warehouse Distance"].apply(
                    lambda d: less_dist_value if pd.notna(d) and d <= 100 else high_dist_value)
                
                df.loc[mask, "Freight Discount Amount"] = (
                    df.loc[mask, "Quantity"] * df.loc[mask, "Freight Discount"]
                )

                df = df.drop("Warehouse Distance", axis=1)
                df["Total Credit Note"] += df["Freight Discount Amount"]
                df["Total Discount"] += df["Freight Discount Amount"]
        return df
    
    @staticmethod
    def build_mou_summary(sales_df: pd.DataFrame,selected_year: int,selected_month: int):
        # Read data
        mou = st.session_state["MOU Data"]
        group_df = st.session_state["Group Data"]
        cmr_df = st.session_state["CMR Data"]

        # Month Boundaries
        month_start = pd.Timestamp(selected_year, selected_month, 1)
        month_end = pd.Timestamp(
            selected_year,
            selected_month,
            monthrange(selected_year, selected_month)[1]
        )
        
        sales_period = sales_df[
        (sales_df["Billing Date"] >= month_start) &
        (sales_df["Billing Date"] <= month_end)
    ]
        # Aggregate Sales Volume
        sales_agg = (
        sales_period
        .groupby(["Sold-to Group", "Regional Office","Material Group"], as_index=False)
        .agg({"Quantity": "sum"})
    )

        pp_volume = (
            sales_agg[sales_agg["Material Group"] == "PP"]
            .groupby(["Sold-to Group", "Regional Office"], as_index=False)
            .agg({"Quantity": "sum"})
            .rename(columns={"Quantity": "Total Volume PP"})
        )

        pe_volume = (
            sales_agg[sales_agg["Material Group"].isin(["LLDPE", "HDPE"])]
            .groupby(["Sold-to Group", "Regional Office"], as_index=False)
            .agg({"Quantity": "sum"})
            .rename(columns={"Quantity": "Total Volume PE"})
        )

        # Create base frame from SALES (critical fix)
        base_df = (
            pd.merge(
                pp_volume,
                pe_volume,
                on=["Sold-to Group", "Regional Office"],
                how="outer"
            )
        )

        # Prepare MOU Data
        mou["MOU Start Date"] = pd.to_datetime(mou["MOU Start Date"])
        mou["MOU End Date"] = pd.to_datetime(mou["MOU End Date"])

        mou_active = mou[
            (mou["MOU Start Date"] <= month_end) &
            (mou["MOU End Date"] >= month_start)
        ]

        # mou_active["Sold-to Party"] = mou_active["Sold-to Party"].astype(str)

        mou_active = mou_active.merge(
            group_df[["Sold-to Party", "Sold-to Group"]],
            on="Sold-to Party",
            how="left"
        )

        mou_active["Sold-to Group"] = mou_active["Sold-to Group"].fillna(
            mou_active["Sold-to-Party Name"]
        )

        # Rename specific columns
        mou_active = mou_active.rename(columns={"PP": "MOU PP", "PE": "MOU PE"})
       
        final_df = base_df.merge(
        mou_active,
        on="Sold-to Group",
        how="left"
    )


        # Drop Columns
        final_df = final_df.drop(['Sold-to Party', 'Sold-to-Party Name','MOU Start Date','MOU End Date'], axis=1)

        # Fill missing values
        final_df["MOU PP"] = final_df["MOU PP"].fillna(0)
        final_df["Total Volume PP"] = final_df.get("Total Volume PP", 0).fillna(0)
        final_df["MOU PE"] = final_df["MOU PE"].fillna(0)   
        final_df["Total Volume PE"] = final_df.get("Total Volume PE", 0).fillna(0)

        # Check MOU Group - we need cust group
        return final_df
    
    # Group Columns
    def prepare_group_pivot(filtered_df: pd.DataFrame) -> pd.DataFrame:
        df = filtered_df.copy()

        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)

        group_cols = [
            "Regional Office",
            "Sold-to Group",
            "Sold-to-Party Name",
            "Material Group",
            "Material Description",
        ]

        for col in group_cols:
            df[col] = df[col].fillna("UNKNOWN").astype(str)

        return (
            df.groupby(group_cols, as_index=False)
            .agg({"Quantity": "sum"})
        )

    # Excel view of Group Pivot
    def render_excel_pivot(filtered_df: pd.DataFrame):

        df = discount.prepare_group_pivot(filtered_df)

        gb = GridOptionsBuilder.from_dataframe(df)

        gb.configure_default_column(
            enableRowGroup=True,
            enablePivot=False,
            enableValue=True,
            resizable=True
        )

        gb.configure_column("Quantity", aggFunc="sum")

        gb.configure_grid_options(
            rowGroupPanelShow="always",
            groupDefaultExpanded=1,
            animateRows=True
        )

        grid_options = gb.build()

        AgGrid(
            df,
            gridOptions=grid_options,
            height=600,
            theme="balham",
            enable_enterprise_modules=True,
            fit_columns_on_grid_load=True,
        )