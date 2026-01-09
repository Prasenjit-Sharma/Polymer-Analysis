from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
import json
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.http import MediaInMemoryUpload
import streamlit as st
import pandas as pd
from calendar import monthrange
import numpy as np
import utilities


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
    @st.cache_data(show_spinner=True, ttl=3600)
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
    def apply_discount(filtered_df: pd.DataFrame, monthly_discounts: dict, select_year, select_month):

        df = filtered_df.copy()
        df["Month Credit Note"] = 0.0
        df["Annual Credit Note"] = 0.0
        df["Month Discount"] = 0.0
        df["Net Discount"] = 0.0

        def apply_mask (df,material_groups,disc_start,disc_end):
            mask = (
                    df["Material Group"].isin(material_groups) &
                    (df["Billing Date"] >= disc_start) &
                    (df["Billing Date"] <= disc_end)
                )
            return mask

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
                mask = apply_mask (df,material_groups,disc_start,disc_end)

                df.loc[mask, "Month MOU Discount"] = (month_discount_amount)

                df.loc[mask, "Annual MOU Discount"] = (annual_discount_amount)

                df.loc[mask,"Month Credit Note"] += df.loc[mask,"Month MOU Discount"]*df.loc[mask, "Quantity"]
                df.loc[mask,"Month Discount"] += df.loc[mask,"Month MOU Discount"]
                df.loc[mask,"Net Discount"] += df.loc[mask,"Month MOU Discount"] + df.loc[mask,"Annual MOU Discount"]
                df.loc[mask,"Annual Credit Note"] += df.loc[mask,"Annual MOU Discount"]*df.loc[mask, "Quantity"]
                
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
                mask = apply_mask (df,material_groups,disc_start,disc_end)

                df.loc[mask, "Freight Discount"] = df.loc[mask, "Warehouse Distance"].apply(
                    lambda d: less_dist_value if pd.notna(d) and d <= 100 else high_dist_value)

                df = df.drop("Warehouse Distance", axis=1)

                df.loc[mask,"Month Credit Note"] += df.loc[mask,"Freight Discount"]*df.loc[mask, "Quantity"]
                df.loc[mask,"Month Discount"] += df.loc[mask,"Freight Discount"]
                df.loc[mask,"Net Discount"] += df.loc[mask,"Freight Discount"]
  
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
                mask = apply_mask (df,material_groups,disc_start,disc_end)

                df.loc[mask, "Early Bird Discount"] = (
                    discount_amount
                )

                df.loc[mask,"Month Credit Note"] += df.loc[mask,"Early Bird Discount"]*df.loc[mask, "Quantity"]
                df.loc[mask,"Month Discount"] += df.loc[mask,"Early Bird Discount"]
                df.loc[mask,"Net Discount"] += df.loc[mask,"Early Bird Discount"]

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
                mask = apply_mask (df,material_groups,disc_start,disc_end)

                df.loc[mask, "Price Protection"] = (discount_amount)

                df.loc[mask,"Month Credit Note"] += df.loc[mask,"Price Protection"]*df.loc[mask, "Quantity"]
                df.loc[mask,"Month Discount"] += df.loc[mask,"Price Protection"]
                df.loc[mask,"Net Discount"] += df.loc[mask,"Price Protection"]

        if "X-Y Scheme" in monthly_discounts:
            group_df = pd.DataFrame({'X-Y Scheme': [0]})
            discounts = monthly_discounts["X-Y Scheme"]

            for col in ["X-Y Scheme"]:
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

                material_family = "PP" if "PP" in material_groups else "PE"

                if basis == "MOU%":
                
                    group_df = discount.prepare_mou_group_pivot(df,select_year, select_month)
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
                                                select_year, select_month)
                    group_df = group_df[
                        group_df["Material Family"] == material_family
                    ].copy()
                    # --- SLAB RESOLUTION ---
                    group_df["X-Y Scheme"] = group_df["%Non-Zero Avg"].apply(
                        lambda x: discount.get_slab_amount(x, slabs)
                    )
                    
                # Common Part
                hidden_map = (group_df
                        .set_index("Sold-to Group")["X-Y Scheme"]
                        .to_dict())

                mask = apply_mask (df,material_groups,disc_start,disc_end)

                df.loc[mask, "X-Y Scheme"] += (
                        df.loc[mask, "Sold-to Group"]
                        .map(hidden_map)
                        .fillna(0.0)
                    )    

                df.loc[mask,"Month Credit Note"] += df.loc[mask,"X-Y Scheme"]*df.loc[mask, "Quantity"]
                df.loc[mask,"Month Discount"] += df.loc[mask,"X-Y Scheme"]
                df.loc[mask,"Net Discount"] += df.loc[mask,"X-Y Scheme"]

        if "Hidden Discount" in monthly_discounts:
            
            discounts = monthly_discounts["Hidden Discount"]

            for col in ["Hidden Discount"]:
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

                material_family = "PP" if "PP" in material_groups else "PE"

                if basis == "MOU%":
                
                    group_df = discount.prepare_mou_group_pivot(df,select_year, select_month)
                    group_df = group_df[
                        group_df["Material Family"] == material_family
                    ].copy()
                    # --- SLAB RESOLUTION ---
                    group_df["Hidden Discount"] = group_df["%MOU"].apply(
                        lambda x: discount.get_slab_amount(x, slabs)
                    )
               
                elif basis== "Flat Discount":
                    
                    # --- GROUP-LEVEL TOTAL QUANTITY ---
                    # scheme months == Applicable Material Descriptions
                    group_df = discount.prepare_group_pivot(df,["Sold-to Group","Material Description"])
                    group_df = group_df[
                        group_df["Material Description"].isin(scheme_months)
                    ].copy()
                    # --- SLAB RESOLUTION ---
                    group_df["Hidden Discount"] = group_df["Quantity"].apply(
                        lambda x: discount.get_slab_amount(x, slabs)
                    )
                
                elif basis == "Non-Zero Months Avg%":

                    group_df = discount.prepare_non_zero_avg_group_pivot(df,scheme_months,
                                                select_year, select_month)
                    group_df = group_df[
                        group_df["Material Family"] == material_family
                    ].copy()
                    # --- SLAB RESOLUTION ---
                    group_df["Hidden Discount"] = group_df["%Non-Zero Avg"].apply(
                        lambda x: discount.get_slab_amount(x, slabs)
                    )
                    
                # Common Part
                hidden_map = (
                        group_df
                        .set_index("Sold-to Group")["Hidden Discount"]
                        .to_dict()
                    )

                mask = apply_mask (df,material_groups,disc_start,disc_end)

                # Multiple Hidden Discounts may be applicable
                df["_hidden_rule_discount"] = 0.0

                df.loc[mask, "_hidden_rule_discount"] = (
                    df.loc[mask, "Sold-to Group"]
                    .map(hidden_map)
                    .fillna(0.0)
                )
                
                # Accumulate safely
                df.loc[mask, "Hidden Discount"] += df.loc[mask, "_hidden_rule_discount"]
                df.loc[mask, "Month Credit Note"] += (
                    df.loc[mask, "_hidden_rule_discount"] * df.loc[mask, "Quantity"]
                )
                df.loc[mask,"Month Discount"] += df.loc[mask,"_hidden_rule_discount"]
                df.loc[mask, "Net Discount"] += df.loc[mask, "_hidden_rule_discount"]

                # Cleanup temp column
                df.drop(columns=["_hidden_rule_discount"], inplace=True)
        
        if "Quantity Discount" in monthly_discounts:
            
            discounts = monthly_discounts["Quantity Discount"]

            for col in ["Quantity Discount"]:
                if col not in df.columns:
                    df[col] = 0.0
                else:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            for disc in discounts:
                slabs = disc.get("discount_amount", [])
                material_groups = disc.get("material_groups", [])

                # Normalize material groups (safety)
                if isinstance(material_groups, str):
                    material_groups = [material_groups]

                disc_start = pd.to_datetime(disc["start_date"])
                disc_end = pd.to_datetime(disc["end_date"])

                material_family = "PP" if "PP" in material_groups else "PE"

                # --- GROUP-LEVEL TOTAL QUANTITY ---
                group_df = discount.prepare_group_pivot(df, ["Sold-to Group", "Material Family"])
                
                # --- SLAB RESOLUTION ---
                group_df["Quantity Discount"] = group_df["Quantity"].apply(
                    lambda x: discount.get_slab_amount(x, slabs)
                )

                # Common Part
                hidden_map = (
                        group_df
                        .set_index(["Sold-to Group", "Material Family"])["Quantity Discount"]
                        .to_dict()
                    )

                mask = apply_mask (df,material_groups,disc_start,disc_end)

                df.loc[mask, "Quantity Discount"] += (
                        df.loc[mask]
                        .apply(
                            lambda r: hidden_map.get(
                                (r["Sold-to Group"], r["Material Family"]),
                                0.0
                            ),
                            axis=1
                        ))
                df.loc[mask,"Month Credit Note"] += df.loc[mask,"Quantity Discount"]*df.loc[mask, "Quantity"]
                df.loc[mask,"Month Discount"] += df.loc[mask,"Quantity Discount"]
                df.loc[mask,"Net Discount"] += df.loc[mask,"Quantity Discount"]

        if "Annual Quantity Discount" in monthly_discounts:
            
            discounts = monthly_discounts["Annual Quantity Discount"]

            for col in ["Annual Quantity Discount"]:
                if col not in df.columns:
                    df[col] = 0.0
                else:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            for disc in discounts:
                slabs = disc.get("discount_amount", [])
                material_groups = disc.get("material_groups", [])

                # Normalize material groups (safety)
                if isinstance(material_groups, str):
                    material_groups = [material_groups]

                disc_start = pd.to_datetime(disc["start_date"])
                disc_end = pd.to_datetime(disc["end_date"])

                material_family = "PP" if "PP" in material_groups else "PE"

                # --- GROUP-LEVEL TOTAL QUANTITY ---
                group_df = discount.prepare_annual_quantity_pivot(df, select_year, select_month)

                # --- SLAB RESOLUTION ---
                group_df["Annual Quantity Discount"] = group_df["Annual Expected Quantity"].apply(
                    lambda x: discount.get_slab_amount(x, slabs)
                )
                
                # Common Part
                hidden_map = (
                        group_df
                        .set_index(["Sold-to Group", "Material Family"])["Annual Quantity Discount"]
                        .to_dict()
                    )
                
                mask = apply_mask (df,material_groups,disc_start,disc_end)

                df.loc[mask, "Annual Quantity Discount"] += (
                        df.loc[mask]
                        .apply(
                            lambda r: hidden_map.get(
                                (r["Sold-to Group"], r["Material Family"]),
                                0.0
                            ),
                            axis=1
                        ))
                df.loc[mask,"Annual Credit Note"] += df.loc[mask,"Annual Quantity Discount"]*df.loc[mask, "Quantity"]
                df.loc[mask,"Net Discount"] += df.loc[mask,"Annual Quantity Discount"]

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
    
    # Retrieve Discounts for month
    def filter_discounts_for_month(discount_json, selected_year, selected_month):
        month_start = pd.Timestamp(selected_year, selected_month, 1)
        month_end = pd.Timestamp(selected_year,selected_month,monthrange(selected_year, selected_month)[1])

        applicable_discounts_json = {}

        for discount_type, records in discount_json.items():
            valid_records = []

            for r in records:
                start = pd.to_datetime(r["start_date"])
                end = pd.to_datetime(r["end_date"])

                # overlap logic
                if start <= month_end and end >= month_start:
                    valid_records.append(r)

            if valid_records:
                applicable_discounts_json[discount_type] = valid_records

        return applicable_discounts_json
    
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
        fiscal_year = utilities.get_fiscal_year(selected_month,selected_year)

        full_df = st.session_state["Sales Data"].copy()
        # st.write(full_df)

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

    def prepare_annual_quantity_pivot(df, selected_year: int,selected_month: int):
        mou_df = discount.prepare_mou_group_pivot(df,selected_year,selected_month)
        fiscal_year = utilities.get_fiscal_year(selected_month,selected_year)
        fiscal_df = st.session_state["Sales Data"].copy()
        fiscal_df = fiscal_df[fiscal_df["Fiscal Year"] == fiscal_year]

        fiscal_df = discount.prepare_group_pivot(fiscal_df, ["Sold-to Group", "Material Family"])

        # Remaining Fiscal Months
        if selected_month >= FISCAL_START:
            # Apr–Dec
            rem_no_of_months =  (12 - selected_month) + (FISCAL_START - 1)
        else:
            # Jan–Mar
            rem_no_of_months =  (FISCAL_START - 1) - selected_month
        
        # Merge & Compute %
        pivot = fiscal_df.merge(mou_df,
                                on=["Sold-to Group", "Material Family"],
                                how="left"
                            )
        pivot["Annual Expected Quantity"] = pivot["MOU Qty"]*rem_no_of_months*1.2 + pivot["Quantity"]

        return pivot
    
    def build_sales_mou_summary(mtd_df: pd.DataFrame,mou_df: pd.DataFrame, non_zero_pivot: pd.DataFrame) -> pd.DataFrame:
        df = mtd_df.copy()
        # 1. Ensure correct dtypes

        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0.0)
        mou_df["MOU Qty"] = pd.to_numeric(mou_df["MOU Qty"], errors="coerce").fillna(0.0)

        for col in ["Sold-to Group", "Regional Office", "Material Family",
                    "Material Group", "Material Description"]:
            df[col] = df[col].astype(str)

        mou_df["Sold-to Group"] = mou_df["Sold-to Group"].astype(str)
        mou_df["Material Family"] = mou_df["Material Family"].astype(str)

        # 2. SALES AGGREGATION
        sales_agg = (
            df.groupby(["Regional Office","Sold-to Group","Material Family",
                        "Material Group","Material Description",],as_index=False)["Quantity"].sum())

        # 3. FAMILY TOTALS (PP / PE)

        family_totals = (sales_agg.groupby(["Regional Office", "Sold-to Group", "Material Family"],
                as_index=False)["Quantity"].sum())

        family_totals = family_totals.pivot(
                                        index=["Regional Office", "Sold-to Group"],
                                        columns="Material Family",
                                        values="Quantity").fillna(0.0)

        family_totals = family_totals.rename(columns={"PP": "Total PP Qty","PE": "Total PE Qty"}).reset_index()

        # 4. PIVOT SALES (DETAIL LEVEL)

        sales_pivot = sales_agg.pivot_table(
                                index=["Regional Office", "Sold-to Group"],
                                columns=["Material Family", "Material Group", "Material Description"],
                                values="Quantity",
                                aggfunc="sum",
                                fill_value=0.0)

        # Flatten columns
        sales_pivot.columns = [f"{fam} | {grp} | {desc}"
            for fam, grp, desc in sales_pivot.columns]
        sales_pivot = sales_pivot.reset_index()

        # 5. MOU AGGREGATION (ONCE)

        mou_agg = (mou_df.groupby(["Sold-to Group", "Material Family"],
                            as_index=False)["MOU Qty"]
                            .max()) # IMPORTANT: not sum

        mou_pivot = mou_agg.pivot(
                                index="Sold-to Group",
                                columns="Material Family",
                                values="MOU Qty"
                            ).fillna(0.0)

        mou_pivot = mou_pivot.rename(columns={"PP": "MOU PP Qty","PE": "MOU PE Qty"}).reset_index()

        # 6. MERGE EVERYTHING

        final_df = (sales_pivot
            .merge(family_totals, on=["Regional Office", "Sold-to Group"], how="left")
            .merge(mou_pivot, on="Sold-to Group", how="left"))

        for col in ["MOU PP Qty", "MOU PE Qty"]:
            if col not in final_df:
                final_df[col] = 0.0
            else:
                final_df[col] = final_df[col].fillna(0.0)

        # 7. % OF MOU

        final_df["%PP vs MOU"] = np.where(
            final_df["MOU PP Qty"] > 0,
            (final_df["Total PP Qty"] / final_df["MOU PP Qty"] * 100).round(2),0.0)

        final_df["%PE vs MOU"] = np.where(
            final_df["MOU PE Qty"] > 0,
            (final_df["Total PE Qty"] / final_df["MOU PE Qty"] * 100).round(2),0.0)
        
        # -----------------------------
        # 7. NON-ZERO AVG (FAMILY LEVEL)
        # -----------------------------
        nz = non_zero_pivot.copy()

        # Ensure correct dtypes
        nz["Sold-to Group"] = nz["Sold-to Group"].astype(str)
        nz["Material Family"] = nz["Material Family"].astype(str)
        nz["Non-Zero Avg Qty"] = pd.to_numeric(nz["Non-Zero Avg Qty"], errors="coerce").fillna(0.0)
        nz["%Non-Zero Avg"] = pd.to_numeric(nz["%Non-Zero Avg"], errors="coerce").fillna(0.0)

        # Aggregate once per family (DO NOT SUM)
        nz_agg = (
            nz.groupby(["Sold-to Group", "Material Family"], as_index=False)
            .agg(
                {
                    "Non-Zero Avg Qty": "max",
                    "%Non-Zero Avg": "max"
                }
            )
        )

        # Pivot to family columns
        nz_pivot = nz_agg.pivot(
            index="Sold-to Group",
            columns="Material Family",
            values=["Non-Zero Avg Qty", "%Non-Zero Avg"]
        )

        # Flatten columns
        nz_pivot.columns = [
            f"{metric} {family}"
            for metric, family in nz_pivot.columns
        ]

        nz_pivot = nz_pivot.reset_index()

        # Rename cleanly
        nz_pivot = nz_pivot.rename(
            columns={
                "Non-Zero Avg Qty PP": "Non-Zero Avg PP Qty",
                "%Non-Zero Avg PP": "%PP vs Non-Zero Avg",
                "Non-Zero Avg Qty PE": "Non-Zero Avg PE Qty",
                "%Non-Zero Avg PE": "%PE vs Non-Zero Avg",
            }
        )

        # Merge into final_df
        final_df = final_df.merge(
            nz_pivot,
            on="Sold-to Group",
            how="left"
        )

        # Fill missing
        for col in [
            "Non-Zero Avg PP Qty",
            "%PP vs Non-Zero Avg",
            "Non-Zero Avg PE Qty",
            "%PE vs Non-Zero Avg",
        ]:
            if col not in final_df:
                final_df[col] = 0.0
            else:
                final_df[col] = final_df[col].fillna(0.0)


        # 8. Final column order

        fixed_cols = [
            "Regional Office",
            "Sold-to Group",
            "Total PP Qty",
            "MOU PP Qty",
            "%PP vs MOU",
            "Non-Zero Avg PP Qty",
            "%PP vs Non-Zero Avg",
            "Total PE Qty",
            "MOU PE Qty",
            "%PE vs MOU",
            "Non-Zero Avg PE Qty",
            "%PE vs Non-Zero Avg",
        ]

        other_cols = [c for c in final_df.columns if c not in fixed_cols]

        final_df = final_df[fixed_cols + other_cols]

        return final_df
    
    def build_sales_summary(df: pd.DataFrame, index_list)-> pd.DataFrame:
        full_list = index_list + ["Material Family", "Material Group", "Material Description"]
        agg_list = index_list + ["Material Family"]
        # SALES AGGREGATION
        sales_agg = (
                df.groupby(full_list,as_index=False)["Quantity"].sum())

        # FAMILY TOTALS (PP / PE)

        family_totals = (sales_agg.groupby(agg_list,
                as_index=False)["Quantity"].sum())

        family_totals = family_totals.pivot(
                                        index=index_list,
                                        columns="Material Family",
                                        values="Quantity").fillna(0.0)

        family_totals = family_totals.rename(columns={"PP": "Total PP Qty","PE": "Total PE Qty"}).reset_index()

        # PIVOT SALES (DETAIL LEVEL)

        sales_pivot = sales_agg.pivot_table(
                                index=index_list,
                                columns=["Material Family", "Material Group", "Material Description"],
                                values="Quantity",
                                aggfunc="sum",
                                fill_value=0.0)

        # Flatten columns
        sales_pivot.columns = [f"{fam} | {grp} | {desc}"
            for fam, grp, desc in sales_pivot.columns]
        sales_pivot = sales_pivot.reset_index()

        # 6. MERGE EVERYTHING

        sales_pivot = (sales_pivot
            .merge(family_totals, on=index_list, how="left"))
        
        if ("Month Name" in sales_pivot.columns):
            # Create a mapping for sorting
            month_map = {month: i for i, month in enumerate(utilities.month_order)}
            sales_pivot['month_sort'] = sales_pivot['Month Name'].map(month_map)
            sales_pivot = sales_pivot.sort_values(["Fiscal Year", "month_sort"]).drop('month_sort', axis=1).reset_index(drop=True)

        return sales_pivot