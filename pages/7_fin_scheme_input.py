import streamlit as st
import datetime
import json
import pandas as pd
from discount_calc import discount
from datetime import date

# Function for selecting record
def select_discount_record(existing_json, key_prefix: str):
    discount_type = st.selectbox(
        "Select Discount Type",
        list(existing_json.keys()),
        key=f"{key_prefix}_discount_type"
    )

    records = existing_json[discount_type]

    labels = [
        f"{r['start_date']} → {r['end_date']}"
        for r in records
    ]

    index = st.selectbox(
        "Select Discount Period",
        range(len(labels)),
        format_func=lambda i: labels[i],
        key=f"{key_prefix}_discount_period"
    )

    return discount_type, index, records[index]

# Function for filtering by date
def filter_discounts_by_date(discount_json: dict, start: date, end: date):
    
    start = pd.to_datetime(start).date()
    end = pd.to_datetime(end).date()
    filtered = {}

    for dtype, records in discount_json.items():
        valid_records = []

        for r in records:
            r_start = pd.to_datetime(r["start_date"]).date()
            r_end = pd.to_datetime(r["end_date"]).date()

            # STRICT containment logic
            if r_start <= end and r_end >= start:
                valid_records.append(r)

        if valid_records:
            filtered[dtype] = valid_records

    return filtered

# Date Range Picker
def date_range_selector(key_prefix):
    col1, col2 = st.columns(2)

    with col1:
        start = st.date_input(
            "From Date",
            value=date.today().replace(day=1),
            key=f"{key_prefix}_from"
        )

    with col2:
        end = st.date_input(
            "To Date",
            value=date.today(),
            key=f"{key_prefix}_to"
        )

    if start > end:
        st.error("Start date cannot be after end date")
        st.stop()

    return start, end

st.set_page_config(
    page_title="Monthly Schemes",
    layout="wide"
)

st.subheader("Monthly Schemes")

tab_view, tab_add, tab_modify, tab_delete = st.tabs(
    ["📄 View Discounts", "➕ Add Discount", "✏️ Modify Discount", "🗑️ Delete Discount"]
)

# View Discounts
with tab_view:
    st.markdown("### Existing Discount Schemes")
    start, end = date_range_selector("view")
    try:
        existing_json = discount.read_json_from_drive()
        filtered_json = filter_discounts_by_date(existing_json, start, end)

        if not existing_json:
            st.info("No discount schemes found in the selected date range.")
        else:
            discount.display_discounts_expander(filtered_json)

    except Exception as e:
        st.error(f"Failed to load discounts: {e}")

# Add New Discounts
with tab_add:
    st.markdown("### Add New Discount")
    options_list = ["MOU", "Cash Discount", "Location Discount","Early Bird",
                        "Quantity Discount", "Annual Quantity Discount", "X-Y Scheme"]
    discount_option = st.selectbox(
            "Discount Option",
            options_list,
            index=None,
            placeholder="Select a Discount Type",
            # accept_new_options=True,
        )

    # MOU Discount
    if discount_option == "MOU":
            st.subheader("MOU Discount")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Discount Start Date")
            with col2:
                end_date = st.date_input("Discount End Date")
            with col1:
                month_mou_value = st.number_input("Enter MOU Monthly Component")
            with col2:
                annual_mou_value = st.number_input("Enter MOU Annual Component")
            
            data_to_save = {
                "discount_type": discount_option,
                "start_date": start_date.isoformat() if isinstance(start_date, datetime.date) else None,
                "end_date": end_date.isoformat() if isinstance(end_date, datetime.date) else None,
                "monthly_component": month_mou_value,
                "annual_component": annual_mou_value
            }

    # Cash Discount
    elif discount_option == "Cash Discount":
            st.subheader("Cash Discount")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Discount Start Date")
            with col2:
                end_date = st.date_input("Discount End Date")
            with col1:
                disc_value = st.number_input("Enter Cash Discount")
            
            data_to_save = {
                "discount_type": discount_option,
                "start_date": start_date.isoformat() if isinstance(start_date, datetime.date) else None,
                "end_date": end_date.isoformat() if isinstance(end_date, datetime.date) else None,
                "cash_disc_component": disc_value,
            }

    # Early Bird
    elif discount_option == "Early Bird":
            st.subheader("Early Bird Discount")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Discount Start Date")
            with col2:
                end_date = st.date_input("Discount End Date")
            with col1:
                disc_value = st.number_input("Enter Early Bird Discount")
            
            data_to_save = {
                "discount_type": discount_option,
                "start_date": start_date.isoformat() if isinstance(start_date, datetime.date) else None,
                "end_date": end_date.isoformat() if isinstance(end_date, datetime.date) else None,
                "disc_component": disc_value,
            }

        # Button Saving as JSON
    if discount_option is not None and data_to_save:
            if st.button("Submit and Save"):
                # Convert the Python dictionary to a pretty-printed JSON string
                new_discount = json.dumps(data_to_save, indent=4)
                # Read json file from google drive
                existing_json = discount.read_json_from_drive()
                # Add new discount data
                updated_json = discount.append_discount(existing_json, new_discount)
                # Rewrite file to drive
                discount.overwrite_json_in_drive(updated_json)
                st.success("Data successfully Saved.")
                # st.code(updated_json, language="json")

# Modify Discounts
with tab_modify:
    st.markdown("### Modify Existing Discount")
    start, end = date_range_selector("modify")

    existing_json = discount.read_json_from_drive()
    filtered_json = filter_discounts_by_date(existing_json, start, end)

    if not filtered_json:
        st.info("No discounts available to modify.")
    else:
        dtype, idx, record = select_discount_record(filtered_json, key_prefix="modify")

        st.markdown("#### Edit Selected Discount")

        with st.form("modify_form"):
            updated_record = {}

            for key, value in record.items():
                if "date" in key:
                    updated_record[key] = st.date_input(
                        key.replace("_", " ").title(),
                        pd.to_datetime(value)
                    ).isoformat()
                else:
                    updated_record[key] = st.number_input(
                        key.replace("_", " ").title(),
                        value=float(value)
                    )

            save = st.form_submit_button("Save Changes")

        if save:
            # locate original index in full JSON
            full_index = existing_json[dtype].index(record)
            existing_json[dtype][full_index] = updated_record

            discount.overwrite_json_in_drive(existing_json)
            st.success("Discount updated successfully")
            st.rerun()

# Delete Discounts
with tab_delete:
    st.markdown("### Delete Discount")
    start, end = date_range_selector("delete")

    existing_json = discount.read_json_from_drive()
    filtered_json = filter_discounts_by_date(existing_json, start, end)

    if not filtered_json:
        st.info("No discounts available to delete.")
    else:
        dtype, idx, record = select_discount_record(filtered_json, key_prefix="delete")

        st.warning(
            f"You are about to delete **{dtype}** discount "
            f"({record['start_date']} → {record['end_date']})"
        )

        confirm = st.checkbox("I understand this action cannot be undone")

        if st.button("Delete Discount", disabled=not confirm):
            del existing_json[dtype][idx]

            if not existing_json[dtype]:
                del existing_json[dtype]

            discount.overwrite_json_in_drive(existing_json)
            st.success("Discount deleted successfully")
            st.rerun()