import streamlit as st
import datetime
import json
import pandas as pd
from discount_calc import discount
from datetime import date
from streamlit_calendar import calendar

DISCOUNT_OPTIONS = ["X-Y Scheme","Hidden Discount", "Early Bird", "Price Protection", "Price Change",
                    "MOU Discount","Cash Discount", "Freight Discount", 
                    "Quantity Discount", "Annual Quantity Discount", 
                    ]

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

FISCAL_START = 4  # April
MONTHS = {
    1: "January",  2: "February", 3: "March",
    4: "April",    5: "May",      6: "June",
    7: "July",     8: "August",   9: "September",
    10: "October", 11: "November",12: "December"
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

def scheme_month_selection(key_prefix):
    # Get current month number (1–12)
    current_month = date.today().month
    current_year = date.today().year
    fiscal_year = current_year if current_month >= 4 else current_year - 1

    # Build fiscal year month sequence: Apr → Mar
    fiscal_months = list(range(FISCAL_START, 13)) + list(range(1, FISCAL_START))
    completed_months = fiscal_months[:fiscal_months.index(current_month)]

    # --- UI options ---
    month_options = [MONTHS[i] for i in completed_months]

    selected_names = st.multiselect(
        "Select fiscal months (prior to current month)",
        month_options,
        default=month_options,
        key=f"{key_prefix}_month"
    )

    # --- Reverse lookup (generated on the fly) ---
    selected_numbers = [
        k for k, v in MONTHS.items() if v in selected_names
    ]
    return selected_numbers

def slab_discounts(key_prefix, basis):
    default_df = pd.DataFrame({"Criteria": [80],"Discount Amount": [0.0],})
    slab_df = st.data_editor(
        default_df,
        num_rows="dynamic",
        width='stretch',
        column_config={
            basis : st.column_config.NumberColumn(
                min_value=0,
                required=True
            ),
            "Discount Amount": st.column_config.NumberColumn(
                min_value=0.0,
                required=True
            ),
        },
        key=f"{key_prefix}_slab",
        )

    if slab_df.empty:
        st.error("At least one slab is required.")
        st.stop()

    # Validate ordering
    volumes = slab_df["Criteria"].tolist()
    if volumes != sorted(volumes):
        st.error("Criteria must be in increasing order.")
        st.stop()

    # Build final structure
    discount_amount = []
    for _, row in slab_df.iterrows():
        discount_amount.append(
            {
                "criteria": int(row["Criteria"])
                if not pd.isna(row["Criteria"])
                else None,
                "amount": float(row["Discount Amount"]),
            }
        )
    return discount_amount

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

    # Delete reading discount in Production
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
    # data_to_save={}
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
    elif discount_option == "Freight Discount":
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

    # X-Y Scheme
    elif discount_option == "X-Y Scheme":
            st.subheader("X-Y Scheme")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Discount Start Date")
            with col2:
                end_date = st.date_input("Discount End Date")
            with col1:
                basis = st.selectbox("Basis of Scheme",("MOU%","Non-Zero Months Avg%"))
            with col2:
                if basis == "Non-Zero Months Avg%":
                    selected_numbers = scheme_month_selection(discount_option)
                else:

                    selected_numbers =[]

            discount_amount = slab_discounts(discount_option, basis)
            
            data_to_save = {
            "material_groups": material_group,
            "discount_type": discount_option,
            "start_date": start_date.isoformat() if isinstance(start_date, datetime.date) else None,
            "end_date": end_date.isoformat() if isinstance(end_date, datetime.date) else None,
            "basis": basis,
            "scheme_months": selected_numbers,
            "discount_amount": discount_amount
        }          
    
    # Hidden Scheme
    elif discount_option == "Hidden Discount":
            st.subheader("Hidden Discount")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Discount Start Date")
            with col2:
                end_date = st.date_input("Discount End Date")
            with col1:
                basis = st.selectbox("Basis of Scheme",("Flat Discount","MOU%","Non-Zero Months Avg%"))
            with col2:
                if basis == "Non-Zero Months Avg%":
                    selected_numbers = scheme_month_selection(discount_option)
                else:
                    selected_numbers =[]

            discount_amount = slab_discounts(discount_option, basis)
            
            data_to_save = {
            "material_groups": material_group,
            "discount_type": discount_option,
            "start_date": start_date.isoformat() if isinstance(start_date, datetime.date) else None,
            "end_date": end_date.isoformat() if isinstance(end_date, datetime.date) else None,
            "basis": basis,
            "scheme_months": selected_numbers,
            "discount_amount": discount_amount
        }          

    # Quantity Scheme
    elif discount_option == "Quantity Discount":
            st.subheader("Quantity Discount")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Discount Start Date")
            with col2:
                end_date = st.date_input("Discount End Date")
            basis = "Volumes"

            discount_amount = slab_discounts(discount_option, basis)
            
            data_to_save = {
            "material_groups": material_group,
            "discount_type": discount_option,
            "start_date": start_date.isoformat() if isinstance(start_date, datetime.date) else None,
            "end_date": end_date.isoformat() if isinstance(end_date, datetime.date) else None,
            "basis": basis,
            "discount_amount": discount_amount
        }          

    # Annual Quantity Scheme
    elif discount_option == "Annual Quantity Discount":
            st.subheader("Annual Quantity Discount")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Discount Start Date")
            with col2:
                end_date = st.date_input("Discount End Date")
            basis = "Volumes"

            discount_amount = slab_discounts(discount_option, basis)
            
            data_to_save = {
            "material_groups": material_group,
            "discount_type": discount_option,
            "start_date": start_date.isoformat() if isinstance(start_date, datetime.date) else None,
            "end_date": end_date.isoformat() if isinstance(end_date, datetime.date) else None,
            "basis": basis,
            "discount_amount": discount_amount
        }          


    # Price Change
    elif discount_option == "Price Change":
            st.subheader("Price Change")
            col1, col2 = st.columns(2)
            with col1:
                start_date = end_date = st.date_input("Price Change Date")
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
    if discount_option is not None:
            if st.button("Submit and Save"):
                # Convert the Python dictionary to a pretty-printed JSON string
                new_discount = data_to_save
                # Read json file from google drive
                current_add_json = discount.read_json_from_drive(force_reload=True)
                # Add new discount data
                updated_json = discount.append_discount(current_add_json, new_discount)
                # Rewrite file to drive
                discount.overwrite_json_in_drive(updated_json)
                # st.success(data_to_save)
                st.success("Data successfully Saved.")
                # st.code(updated_json, language="json")

# Modify Discounts
with tab_modify:
    st.markdown("### Modify Existing Discount")

    start, end = date_range_selector("modify")
    current_mod_json = discount.read_json_from_drive(force_reload=True)

    filtered_json = filter_discounts_by_date(current_mod_json, start, end)

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
            full_index = find_record_index(
            current_mod_json[dtype],
            record,
            discount_type=dtype
            )

            current_mod_json[dtype][full_index] = updated_record

            discount.overwrite_json_in_drive(current_mod_json)
            st.success("Discount updated successfully")
            # st.rerun()

# Delete Discounts
with tab_delete:
    st.markdown("### Delete Discount")
    start, end = date_range_selector("delete")

    current_del_json = discount.read_json_from_drive(force_reload=True)

    filtered_json = filter_discounts_by_date(current_del_json, start, end)
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
                current_del_json[dtype],
                record,
                discount_type=dtype
            )

            del current_del_json[dtype][full_index]

            # Clean up empty discount type
            if not current_del_json[dtype]:
                del current_del_json[dtype]

            discount.overwrite_json_in_drive(current_del_json)
            st.success("Discount deleted successfully")
            # st.rerun()