import streamlit as st
import datetime
import json
import pandas as pd
from discount_calc import discount
from datetime import date
from streamlit_calendar import calendar

DISCOUNT_OPTIONS = ["MOU Discount", "Cash Discount", "Freight Discount","Early Bird",
                        "Quantity Discount", "Annual Quantity Discount", "X-Y Scheme",
                        "Price Protection", "Price Change"]

DISCOUNT_COLORS = {
    "MOU": "#1f77b4",
    "Cash Discount": "#2ca02c",
    "Early Bird": "#ff7f0e",
    "Freight Discount": "#155b5b"
}

PRICE_CHANGE_STYLE = {
    "Increase": {"direction": "▲", "color": "#2ecc71"},  # green
    "Decrease": {"direction": "▼", "color": "#e74c3c"},  # red
}

# Discount Amount
def format_discount_amount(record):
    return f"Amt: {record.get('discount_amount', 0)}"

# Display Discount in Calendar
def discounts_to_calendar_events(discount_json: dict, selected_groups, selected_discount_types):
    events = []

    for discount_type, records in discount_json.items():
        if discount_type not in selected_discount_types:
            continue
        for r in records:
            record_groups = r.get("material_groups", [])

            # BACKWARD-COMPATIBILITY FIX
            if isinstance(record_groups, str):
                record_groups = [record_groups]

            if not set(record_groups).intersection(selected_groups):
                continue

            amount_text = format_discount_amount(r)
            if discount_type == "Price Change":
                style = PRICE_CHANGE_STYLE.get(r["direction"], {})
                events.append({
                    "title": f"Price: {style['direction']} | {amount_text}",
                    "start": r["start_date"],
                    "end": r["end_date"],
                    "color": style["color"],
                    "extendedProps": r  # keeps all data for future clicks
                })

            else:
                events.append({
                    "title": f"{discount_type} | {amount_text}",
                    "start": r["start_date"],
                    "end": r["end_date"],
                    "color": DISCOUNT_COLORS.get(discount_type, "#888888"),
                    "extendedProps": r  # keeps all data for future clicks
                })

    return events

# Calendar View Options
calendar_options = {
    "initialView": "dayGridMonth",
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek,timeGridDay"
    },
    "editable": False,
    "selectable": False,
    "height": "auto"
}

# FRAGMENT (NO RELOAD ON SCROLL)
@st.fragment
def render_calendar(events):
    calendar(
        events=events,
        options=calendar_options
    )

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

# Find Record Index
def find_record_index(records, target_record, discount_type):
    target_groups = target_record.get("material_groups", [])
    if isinstance(target_groups, str):
        target_groups = [target_groups]

    for i, r in enumerate(records):
        if (
            r["start_date"] == target_record["start_date"]
            and r["end_date"] == target_record["end_date"]
            and set(r.get("material_groups", [])) == set(target_groups)
        ):
            return i

    raise ValueError("Record not found in original data")

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
    st.markdown("### Discount Calendar View")

    existing_json = st.session_state["Discount Data"] 
    col1, col2 = st.columns([2, 3])

    with col1:
        selected_groups = st.multiselect(
            "Material Group",
            ["PP", "LLDPE", "HDPE"],
            default=["PP"],
            key="view_material_group"
        )

    with col2:
        selected_discount_types = st.multiselect(
            "Discount Type",
            list(discount.read_json_from_drive().keys()),
            default=list(discount.read_json_from_drive().keys()),
            key="view_discount_types"
        )

    if not existing_json:
        st.info("No discount schemes configured.")
    else:
        events = discounts_to_calendar_events(existing_json,selected_groups, selected_discount_types)
        render_calendar(events)

# Add New Discounts
with tab_add:
    st.markdown("### Add New Discount")
    
    # Material Group Options
    material_group = st.multiselect(
        "Material Group",
        ["PP", "LLDPE", "HDPE"],
        default=["PP", "LLDPE", "HDPE"],
        key="add_material_group"
        )
    if isinstance(material_group, str):
        material_group = [material_group]

    # Discount options
    discount_option = st.selectbox(
            "Discount Option",
            DISCOUNT_OPTIONS,
            index=None,
            placeholder="Select a Discount Type",
            # accept_new_options=True,
        )

    # MOU Discount
    if discount_option == "MOU Discount":
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
            
            discount_amount = month_mou_value+annual_mou_value
            data_to_save = {
                "material_groups": material_group,
                "discount_type": discount_option,
                "start_date": start_date.isoformat() if isinstance(start_date, datetime.date) else None,
                "end_date": end_date.isoformat() if isinstance(end_date, datetime.date) else None,
                "monthly_component": month_mou_value,
                "annual_component": annual_mou_value,
                "discount_amount": discount_amount
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
                discount_amount = st.number_input("Enter Cash Discount")
            
            data_to_save = {
                "material_groups": material_group,
                "discount_type": discount_option,
                "start_date": start_date.isoformat() if isinstance(start_date, datetime.date) else None,
                "end_date": end_date.isoformat() if isinstance(end_date, datetime.date) else None,
                "discount_amount": discount_amount
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
                discount_amount = st.number_input("Enter Early Bird Discount")
            
            data_to_save = {
                "material_groups": material_group,
                "discount_type": discount_option,
                "start_date": start_date.isoformat() if isinstance(start_date, datetime.date) else None,
                "end_date": end_date.isoformat() if isinstance(end_date, datetime.date) else None,
                "discount_amount": discount_amount,
            }

    # Price Protection
    elif discount_option == "Price Protection":
            st.subheader("Price Protection")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Discount Start Date")
            with col2:
                end_date = st.date_input("Discount End Date")
            with col1:
                discount_amount = st.number_input("Enter Price Protection Amount")
            
            data_to_save = {
                "material_groups": material_group,
                "discount_type": discount_option,
                "start_date": start_date.isoformat() if isinstance(start_date, datetime.date) else None,
                "end_date": end_date.isoformat() if isinstance(end_date, datetime.date) else None,
                "discount_amount": discount_amount,
            }

    # Freight Discount
    if discount_option == "Freight Discount":
            st.subheader("Freight Discount")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Discount Start Date")
            with col2:
                end_date = st.date_input("Discount End Date")
            with col1:
                less_dist_value = st.number_input("Enter Discount for Less than 100 km", key="less_frieght")
            with col2:
                high_dist_value = st.number_input("Enter Discount for Less than 100 km", key="high_frieght")
            
            discount_amount = high_dist_value
            data_to_save = {
                "material_groups": material_group,
                "discount_type": discount_option,
                "start_date": start_date.isoformat() if isinstance(start_date, datetime.date) else None,
                "end_date": end_date.isoformat() if isinstance(end_date, datetime.date) else None,
                "less_dist_value": less_dist_value,
                "high_dist_value": high_dist_value,
                "discount_amount": discount_amount
            }
    # Price Change
    elif discount_option == "Price Change":
            st.subheader("Early Bird Discount")
            col1, col2 = st.columns(2)
            with col1:
                start_date = end_date = st.date_input("Price Chnage Date")
            with col2:
                direction = st.selectbox("Direction",["Increase","Decrease"],placeholder="Select Direction")
            with col1:
                discount_amount = st.number_input("Enter Price Change Amount")
            
            data_to_save = {
                "material_groups": material_group,
                "discount_type": discount_option,
                "direction" : direction,
                "start_date": start_date.isoformat() if isinstance(start_date, datetime.date) else None,
                "end_date": end_date.isoformat() if isinstance(end_date, datetime.date) else None,
                "discount_amount": discount_amount,
            }

    # Button Saving as JSON
    if discount_option is not None and data_to_save:
            if st.button("Submit and Save"):
                # Convert the Python dictionary to a pretty-printed JSON string
                # new_discount = json.dumps(data_to_save, indent=4)
                new_discount = data_to_save
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
                label = key.replace("_", " ").title()

                # --- Dates ---
                if key.endswith("_date") and value:
                    updated_record[key] = st.date_input(
                        label,
                        pd.to_datetime(value),
                        key=f"edit_{key}_{dtype}"
                    ).isoformat()

                # --- Material Groups (LIST[str]) ---
                elif key == "material_groups":
                    updated_record[key] = st.multiselect(
                        label,
                        ["PP", "LLDPE", "HDPE"],
                        default=value,
                        key=f"edit_{key}_{dtype}"
                    )

                # --- Numeric values ---
                elif isinstance(value, (int, float)):
                    updated_record[key] = st.number_input(
                        label,
                        value=float(value),
                        min_value=0.0,
                        key=f"edit_{key}_{dtype}"
                    )

                # --- String values ---
                elif isinstance(value, str):
                    updated_record[key] = st.text_input(
                        label,
                        value=value,
                        key=f"edit_{key}_{dtype}"
                    )

                # --- Fallback (do not edit) ---
                else:
                    updated_record[key] = value 

            save = st.form_submit_button("Save Changes")

        if save:
            # locate original index in full JSON
            # full_index = existing_json[dtype].index(record)
            # existing_json[dtype][full_index] = updated_record

            full_index = find_record_index(
            existing_json[dtype],
            record,
            discount_type=dtype
            )

            existing_json[dtype][full_index] = updated_record

            discount.overwrite_json_in_drive(existing_json)
            st.success("Discount updated successfully")
            st.rerun()

# Delete Discounts
with tab_delete:
    st.markdown("### Delete Discount")
    start, end = date_range_selector("delete")

    # Material Group selector
    selected_groups = st.multiselect(
        "Material Group",
        ["PP", "LLDPE", "HDPE"],
        default=["PP", "LLDPE", "HDPE"],
        key="delete_material_groups"
    )

    # Further filter by material groups
    filtered_json = {
        dtype: [
            r for r in records
            if set(
                r.get("material_groups")
                or r.get("material_group")
                or []
            ).intersection(selected_groups)
        ]
        for dtype, records in filtered_json.items()
        if [
            r for r in records
            if set(
                r.get("material_groups")
                or r.get("material_group")
                or []
            ).intersection(selected_groups)
        ]
    }

    if not filtered_json:
        st.info("No discounts available to delete for the selected filters.")
    else:
        # Select discount + record
        dtype, idx, record = select_discount_record(
            filtered_json,
            key_prefix="delete"
        )

        st.warning(
            f"""
            You are about to delete **{dtype}** discount  
            **Period:** {record['start_date']} → {record['end_date']}  
            **Material Groups:** {", ".join(record.get("material_groups", []))}
            """
        )

        confirm = st.checkbox(
            "I understand this action cannot be undone",
            key="delete_confirm"
        )

        if st.button("Delete Discount", disabled=not confirm):
            # Find correct index in original (unfiltered) JSON
            full_index = find_record_index(
                existing_json[dtype],
                record,
                discount_type=dtype
            )

            del existing_json[dtype][full_index]

            # Clean up empty discount type
            if not existing_json[dtype]:
                del existing_json[dtype]

            discount.overwrite_json_in_drive(existing_json)
            st.success("Discount deleted successfully")
            st.rerun()