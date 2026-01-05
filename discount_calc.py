from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
import json
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.http import MediaInMemoryUpload
import streamlit as st
import pandas as pd
from calendar import monthrange
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

FISCAL_START = 4  # April

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
    @st.cache_data(show_spinner=True)
    def read_json_from_drive(cache_version: int):
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

    # Applying Discount
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
                    annual_discount_amount
                )
                df.loc[mask, "Annual MOU Discount Amount"] = (
                    df.loc[mask, "Quantity"] * annual_discount_amount
                )
                df["Total Credit Note"] += df["Month MOU Discount Amount"].fillna(0)
                df["Total Discount"] += df["Month MOU Discount Amount"].fillna(0) + df["Annual MOU Discount Amount"].fillna(0)
        
        if "Early Bird" in monthly_discounts:
            
            discounts = monthly_discounts["Early Bird"]
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
                df["Total Credit Note"] += df["Early Bird Amount"].fillna(0)
                df["Total Discount"] += df["Early Bird Amount"].fillna(0)

        if "Price Protection" in monthly_discounts:
            
            discounts = monthly_discounts["Price Protection"]
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
                
                df["Total Credit Note"] += df["Price Protection Amount"].fillna(0)
                df["Total Discount"] += df["Price Protection Amount"].fillna(0)
        
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
                df["Total Credit Note"] += df["Freight Discount Amount"].fillna(0)
                df["Total Discount"] += df["Freight Discount Amount"].fillna(0)
        
        if "Hidden Discount" in monthly_discounts:
            
            discounts = monthly_discounts["Hidden Discount"]

            for col in ["Hidden Discount", "Hidden Discount Amount"]:
                if col not in df.columns:
                    df[col] = 0.0
                else:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            for disc in discounts:
                slabs = disc.get("discount_amount", [])
                material_groups = disc.get("material_groups", [])
                basis = disc.get("basis",[])

                # Normalize material groups (safety)
                if isinstance(material_groups, str):
                    material_groups = [material_groups]

                disc_start = pd.to_datetime(disc["start_date"])
                disc_end = pd.to_datetime(disc["end_date"])
                selected_year = disc_start.year
                selected_month = disc_start.month


                if "PP" in material_groups:
                    material_family = "PP"
                    valid_materials = ["PP"]
                else:
                    material_family = "PE"
                    valid_materials = ["LLDPE", "HDPE"]

                if basis == "MOU%":
                
                    # if "PP" in material_groups:
                    #     mou_col = "%MOU PP"
                    # else:
                    #     mou_col = "%MOU PE"
                    # group_df = discount.mou_sales_summary2(filtered_df,selected_year,selected_month)
                    # group_df["Hidden Discount"] = group_df[mou_col].apply(
                    #     lambda x: discount.get_slab_amount(x, slabs)
                    # )
                    group_df = discount.prepare_mou_group_pivot(df,selected_year, selected_month)
                    group_df = group_df[
                        group_df["Material Family"] == material_family
                    ].copy()
                    # --- SLAB RESOLUTION ---
                    group_df["Hidden Discount"] = group_df["%MOU"].apply(
                        lambda x: discount.get_slab_amount(x, slabs)
                    )
               
                elif basis== "Flat Discount":
                    
                     # --- GROUP-LEVEL TOTAL QUANTITY ---
                    group_df = (
                        df.groupby("Sold-to Group", as_index=False)["Quantity"].sum())
                    
                    # --- SLAB RESOLUTION ---
                    group_df["Hidden Discount"] = group_df["Quantity"].apply(
                        lambda x: discount.get_slab_amount(x, slabs)
                    )
                
                elif basis == "Non-Zero Months Avg%":

                    group_df = discount.prepare_non_zero_avg_group_pivot(df,scheme_months,
                                                selected_year, selected_month)
                    group_df = group_df[
                        group_df["Material Family"] == material_family
                    ].copy()
                    # --- SLAB RESOLUTION ---
                    group_df["X-Y Scheme"] = group_df["%Non-Zero Avg"].apply(
                        lambda x: discount.get_slab_amount(x, slabs)
                    )
                    
                # Common Part
                hidden_map = (
                        group_df
                        .set_index("Sold-to Group")["Hidden Discount"]
                        .to_dict()
                    )
                assign_mask = (
                        df["Material Group"].isin(valid_materials) &
                        (df["Billing Date"] >= disc_start) &
                        (df["Billing Date"] <= disc_end)
                    )
                df.loc[assign_mask, "Hidden Discount"] += (
                        df.loc[assign_mask, "Sold-to Group"]
                        .map(hidden_map)
                        .fillna(0.0)
                    )    
                df.loc[mask, "Hidden Discount Amount"] += (
                        df.loc[mask, "Quantity"] * df.loc[mask, "Hidden Discount"]
                    )
                
                df["Total Credit Note"] += df["Hidden Discount Amount"].fillna(0)
                df["Total Discount"] += df["Hidden Discount Amount"].fillna(0)

        if "X-Y Scheme" in monthly_discounts:
            group_df = pd.DataFrame({'X-Y Scheme': [0]})
            discounts = monthly_discounts["X-Y Scheme"]

            for col in ["X-Y Scheme", "X-Y Scheme Amount"]:
                if col not in df.columns:
                    df[col] = 0.0
                else:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            for disc in discounts:
                slabs = disc.get("discount_amount", [])
                material_groups = disc.get("material_groups", [])
                basis = disc.get("basis",[])
                scheme_months = disc.get("scheme_months", [])

                # Normalize material groups (safety)
                if isinstance(material_groups, str):
                    material_groups = [material_groups]

                disc_start = pd.to_datetime(disc["start_date"])
                disc_end = pd.to_datetime(disc["end_date"])
                selected_year = disc_start.year
                selected_month = disc_start.month


                if "PP" in material_groups:
                    material_family = "PP"
                    valid_materials = ["PP"]
                else:
                    material_family = "PE"
                    valid_materials = ["LLDPE", "HDPE"]

                if basis == "MOU%":
                
                    # if "PP" in material_groups:
                    #     mou_col = "%MOU PP"
                    # else:
                    #     mou_col = "%MOU PE"
                    # group_df = discount.mou_sales_summary2(filtered_df,selected_year,selected_month)
                    # group_df["X-Y Scheme"] = group_df[mou_col].apply(
                    #     lambda x: discount.get_slab_amount(x, slabs)
                    # )
                    group_df = discount.prepare_mou_group_pivot(df,selected_year, selected_month)
                    group_df = group_df[
                        group_df["Material Family"] == material_family
                    ].copy()
                    # --- SLAB RESOLUTION ---
                    group_df["X-Y Scheme"] = group_df["%MOU"].apply(
                        lambda x: discount.get_slab_amount(x, slabs)
                    )
               
                elif basis== "Flat Discount":
                    
                     # --- GROUP-LEVEL TOTAL QUANTITY ---
                    group_df = (
                        df.groupby("Sold-to Group", as_index=False)["Quantity"].sum())
                    
                    # --- SLAB RESOLUTION ---
                    group_df["X-Y Scheme"] = group_df["Quantity"].apply(
                        lambda x: discount.get_slab_amount(x, slabs)
                    )

                elif basis == "Non-Zero Months Avg%":

                    group_df = discount.prepare_non_zero_avg_group_pivot(df,scheme_months,
                                                selected_year, selected_month)
                    group_df = group_df[
                        group_df["Material Family"] == material_family
                    ].copy()
                    # --- SLAB RESOLUTION ---
                    group_df["X-Y Scheme"] = group_df["%Non-Zero Avg"].apply(
                        lambda x: discount.get_slab_amount(x, slabs)
                    )
                    
                # Common Part
                hidden_map = (
                        group_df
                        .set_index("Sold-to Group")["X-Y Scheme"]
                        .to_dict()
                    )
                assign_mask = (
                        df["Material Group"].isin(valid_materials) &
                        (df["Billing Date"] >= disc_start) &
                        (df["Billing Date"] <= disc_end)
                    )
                df.loc[assign_mask, "X-Y Scheme"] += (
                        df.loc[assign_mask, "Sold-to Group"]
                        .map(hidden_map)
                        .fillna(0.0)
                    )    
                df.loc[mask, "X-Y Scheme Amount"] += (
                        df.loc[mask, "Quantity"] * df.loc[mask, "X-Y Scheme"]
                    )
                
                df["Total Credit Note"] += df["X-Y Scheme Amount"].fillna(0)
                df["Total Discount"] += df["X-Y Scheme Amount"].fillna(0)

        return df
    
    # Retreive Slab Discount
    def get_slab_amount(quantity: float, slabs: list[dict]) -> float:
        """
        slabs: list of dicts with keys: criteria, amount
        Rule: highest criteria <= quantity wins
        """
        applicable = [
            s["amount"]
            for s in slabs
            if quantity >= s["criteria"]
        ]
        return max(applicable) if applicable else 0.0
    
    
    # Grouping Sales Data
    def prepare_group_pivot(filtered_df: pd.DataFrame, group_cols) -> pd.DataFrame:
        df = filtered_df.copy()

        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)

        for col in group_cols:
            df[col] = df[col].fillna("UNKNOWN").astype(str)

        return (
            df.groupby(group_cols, as_index=False)
            .agg({"Quantity": "sum"})
        )

    def prepare_mou_group_pivot(df: pd.DataFrame,selected_year: int,selected_month: int):
        # Current Month Quantity

        current_qty = discount.prepare_group_pivot(df, ["Sold-to Group", "Material Family"])
        current_qty = current_qty.rename(columns={"Quantity": "Current Month Qty"})

        # Month Boundaries
        month_start = pd.Timestamp(selected_year, selected_month, 1)
        month_end = pd.Timestamp(selected_year,selected_month,
            monthrange(selected_year, selected_month)[1])
        # Mou Data
        mou_df = st.session_state["MOU Data"]

        # Flatten MOU DF
        mou_df = pd.melt(mou_df, id_vars=["Sold-to Party","Sold-to-Party Name","Sold-to Group",
                               "MOU Start Date","MOU End Date"], 
                               var_name='Material Family', value_name='MOU Qty')

        mou_active = mou_df[
                            (mou_df["MOU Start Date"] <= month_end) &
                            (mou_df["MOU End Date"] >= month_start)]
        
        # Merge & Compute %
        pivot = current_qty.merge(mou_active,
                                on=["Sold-to Group", "Material Family"],
                                how="left"
                            )
        pivot["MOU Qty"] = pivot["MOU Qty"].fillna(0.0)
        
        # % MOU
        pivot["%MOU"] = ((pivot["Current Month Qty"] / pivot["MOU Qty"]*100)
                    .replace([float("inf"), -float("inf")], 0).fillna(0).round(2))

        return pivot

    def prepare_non_zero_avg_group_pivot(df: pd.DataFrame,scheme_months: list[int],
                        selected_year: int,selected_month: int) -> pd.DataFrame:
        
        # Determine Fiscal Year

        if selected_month >= FISCAL_START:
            fiscal_year = selected_year
        else:
            fiscal_year = selected_year - 1

        full_df = st.session_state["Sales Data"].copy()

        # Current Month Quantity

        current_qty = discount.prepare_group_pivot(df, ["Sold-to Group", "Material Family"])
        current_qty = current_qty.rename(columns={"Quantity": "Current Month Qty"})

        # 4. Build fiscal historical window
        def map_fiscal_year(row):
            return row["Year"] if row["Month"] >= FISCAL_START else row["Year"] - 1

        full_df["Fiscal Year"] = full_df.apply(map_fiscal_year, axis=1)

        history_df = full_df[
            (full_df["Fiscal Year"] == fiscal_year) &
            (full_df["Month"].isin(scheme_months))
        ]

        # Monthly Quantity Aggregation
        monthly_qty = discount.prepare_group_pivot(history_df,["Sold-to Group", "Material Family", "Month"])

        # Non-Zero Month Average
        non_zero_avg = (
            monthly_qty[monthly_qty["Quantity"] > 0]
            .groupby(
                ["Sold-to Group", "Material Family"],
                as_index=False
            )["Quantity"]
            .mean()
            .rename(columns={"Quantity": "Non-Zero Avg Qty"})
        )

        # Merge & Compute %
        pivot = current_qty.merge(non_zero_avg,
                                on=["Sold-to Group", "Material Family"],
                                how="left"
                            )
        pivot["Non-Zero Avg Qty"] = pivot["Non-Zero Avg Qty"].fillna(0.0)

        # % Non Zero
        pivot["%Non-Zero Avg"] = ((pivot["Current Month Qty"] / pivot["Non-Zero Avg Qty"]*100)
                    .replace([float("inf"), -float("inf")], 0).fillna(0).round(2))

        return pivot

    # Display Aggrid view of Group Pivot
    def render_excel_pivot(df,key):

        gb = GridOptionsBuilder.from_dataframe(df)

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
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        for col in numeric_cols:
            gb.configure_column(
                col,
                aggFunc="sum",
                type=["numericColumn"],
                valueFormatter="x == null ? '' : x.toLocaleString('en-IN')"
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
            df,
            gridOptions=grid_options,
            height=600,
            theme="balham",
            enable_enterprise_modules=True,
            allow_unsafe_jscode=True,
            update_mode="NO_UPDATE",
            key=key
        )