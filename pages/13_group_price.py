import streamlit as st
import pandas as pd
from reading_gsheet_data import read_data
import utilities

utilities.apply_common_styles("Group Price Finder")


# =========================================================
# CONFIG
# =========================================================

SPREADSHEET_URL = st.secrets["pricing"]["GROUP_MASTER_SHEET"]


# =========================================================
# GOOGLE SHEETS CONNECTION
# =========================================================



# =========================================================
# SESSION STATE
# =========================================================

if "rows" not in st.session_state:

    st.session_state.rows = [
        {
            "company": "",
            "family": "",
            "grade": "",
            "location": "",
            "price_point": "",
            "delivery_location": ""
        }
    ]

# =========================================================
# FUNCTIONS
# =========================================================

def add_row():

    st.session_state.rows.append(
        {
            "company": "",
            "family": "",
            "category":"",
            "grade": "",
            "location": "",
            "price_point": "",
            "delivery_location": ""
        }
    )

def delete_row(index):
    st.session_state.rows.pop(index)

# =========================================================
# UI
# =========================================================

tab_price, tab_create, tab_modify, tab_delete = st.tabs(["Find Price","Create Group","Modify Group","Delete Group"])

# =========================================================
# SESSION STATE
# =========================================================

if "price_output_df" not in st.session_state:
    st.session_state.price_output_df = None

# =========================================================
# TAB PRICE
# =========================================================

with tab_price:

    # =====================================
    # CACHED GROUP READ
    # =====================================
    
    col1, col2 = st.columns([1,5])

    with col1:

        if st.button("🔄 Refresh Groups"):
            read_data.read_groups_data.clear()
            st.rerun()
    group_df = read_data.read_groups_data(SPREADSHEET_URL)
    

    if group_df.empty:
        st.warning("No groups found")
    else:
        

        # =====================================
        # INPUT FORM
        # =====================================

        with st.container(border=True):

            col1, col2, col3, col4, col5, col6 = st.columns(6)
            temp_df = group_df

            with col1:
                price_date = st.date_input( "Price Date", format="DD/MM/YYYY")
            
            with col2:
                all_family = sorted(temp_df["family"].unique())
                selected_family = st.selectbox("Family", all_family)
                temp_df = temp_df[temp_df["family"]== selected_family]

            with col3:
                all_category = sorted(temp_df["category"].unique())
                selected_category = st.selectbox("category", all_category)
                temp_df = temp_df[temp_df["category"]== selected_category]
                

            with col4:
                all_location = sorted(temp_df["location"].unique())
                selected_location = st.selectbox("Location", all_location)
                temp_df = temp_df[temp_df["location"]== selected_location]
                
            with col5:
                all_price_point = sorted(temp_df["price_point"].unique())
                selected_price_point = st.selectbox("Price Point", all_price_point)
                temp_df = temp_df[temp_df["price_point"]== selected_price_point]

            with col6:
                all_groups = sorted(temp_df["group_name"].unique())
                selected_group = st.selectbox("Group Name", all_groups)

            # submit_price = st.form_submit_button("Get Prices")
            submit_price = st.button("Get Prices")
        # =====================================
        # FETCH PRICES
        # =====================================

        if submit_price:

            selected_group_df = group_df[group_df["group_name"]== selected_group].reset_index(drop=True)
            output_rows = []
            progress_bar = st.progress(0)
            total_rows = len(selected_group_df)
            

            for idx, row in (selected_group_df.iterrows()):

                company = row["company"]
                family = row["family"]
                grade = row["grade"]
                location = row["location"]
                price_point = row["price_point"]
                delivery_location = row["delivery_location"]
                price = 0
                freight = 0
                
                try:

                    (spreadsheet_name, freight_sheet_name) = (utilities.get_spreadsheet_name(
                                        company, family, price_point))

                    # =========================
                    # PRICE
                    # =========================

                    (price_df, circular_date) = (read_data.read_pricing_data_cached(
                                    spreadsheet_name, price_date))

                    price,msg = utilities.get_price(price_df, grade, location)
                    # st.write(company, price)

                    if msg == "No matching location found":
                        st.write("I am here")
                        price = 0

                except:
                    price = 0

                # =========================
                # FREIGHT
                # =========================

                if (price_point == "Plant" and company in utilities.SPECIAL_FREIGHT_COMPANIES):
                    try:
                        (freight_df, freight_date) = (read_data.read_freight_data_cached(
                                freight_sheet_name,price_date))

                        freight = (utilities.get_freight(freight_df, delivery_location))

                        if freight is None:
                            freight = 0

                    except:
                        freight = 0

                # =========================
                # OUTPUT
                # =========================
                # st.write(company, price, freight)
                output_rows.append({
                    "Company": company,
                    # "Family": family,
                    "Grade": grade,
                    # "Location": location,
                    # "Price Point": price_point,
                    # "Delivery Location": delivery_location,
                    "Price": price,
                    "Freight": freight,
                    "Net Price": price + freight
                })

                progress_bar.progress((idx + 1) / total_rows)

            progress_bar.empty()

            st.session_state.price_output_df = (pd.DataFrame(output_rows))

    # =====================================
    # DATA EDITOR
    # =====================================

    if (st.session_state.price_output_df is not None):

        edited_df = st.data_editor(
            st.session_state.price_output_df,
            use_container_width=True,
            num_rows="dynamic",
            key="price_editor",
            disabled=[
                "Company",
                # "Family",
                "Grade",
                # "Location",
                # "Price Point",
                # "Delivery Location",
                "Net Price"
            ]
        )

        # =================================
        # RECALCULATE BUTTON
        # =================================

        recalculate_clicked = st.button("Recalculate Net Price")

        if recalculate_clicked:

            edited_df["Price"] = pd.to_numeric(edited_df["Price"], errors="coerce").fillna(0)

            edited_df["Freight"] = pd.to_numeric(edited_df["Freight"], errors="coerce").fillna(0)

            edited_df["Net Price"] = (edited_df["Price"] + edited_df["Freight"])

            # Save updated dataframe
            st.session_state.price_output_df = (edited_df.copy())

            st.rerun()

        # =================================
        # TOTALS
        # =================================

        totals = pd.DataFrame([{

            "Price": pd.to_numeric( edited_df["Price"], errors="coerce").fillna(0).sum(),

            "Freight": pd.to_numeric( edited_df["Freight"], errors="coerce").fillna(0).sum(),

            "Net Price": pd.to_numeric(edited_df["Net Price"], errors="coerce").fillna(0).sum()
        }])

with tab_create:
    with st.form("group_form"):

        for i, row in enumerate(st.session_state.rows):

            cols = st.columns([1,1,1,1,1,1,1,0.4])

            row["company"] = cols[0].selectbox(
                "Company",
                utilities.COMPANIES,
                key=f"company_{i}"
            )

            row["family"] = cols[1].selectbox(
                "Family",
                utilities.FAMILY,
                key=f"family_{i}"
            )

            row["category"] = cols[2].selectbox(
                "Category",
                utilities.CATEGORY,
                key=f"category_{i}"
            )

            row["grade"] = cols[3].text_input(
                "Grade",
                value=row["grade"],
                key=f"grade_{i}"
            )

            row["location"] = cols[4].text_input(
                "Location",
                value=row["location"],
                key=f"location_{i}"
            )

            available_price_points = utilities.PRICE_POINT_MAP.get(
                row["company"],
                []
            )

            row["price_point"] = cols[5].selectbox(
                "Price Point",
                available_price_points,
                key=f"price_point_{i}"
            )

            if (
                row["price_point"] == "Plant"
                and row["company"] in utilities.SPECIAL_FREIGHT_COMPANIES
            ):

                row["delivery_location"] = cols[6].text_input(
                    "Delivery Location",
                    value=row.get("delivery_location", ""),
                    key=f"delivery_location_{i}"
                )

            else:

                row["delivery_location"] = ""

            
            if cols[7].form_submit_button("❌",key=f"delete_button_{i}",use_container_width=True):

                delete_row(i)

                st.rerun()


        add_clicked = st.form_submit_button("➕ Add Row")
        group_name = st.text_input("Group Name",key="group_name")
        save_clicked = st.form_submit_button("💾 Save Group")

        if add_clicked:

            add_row()

            st.rerun()

        if save_clicked:

            spreadsheet,sheet_names = read_data.get_sheet_names(SPREADSHEET_URL)

            worksheet = spreadsheet.worksheet("Groups")
            rows_to_save = []

            for row in st.session_state.rows:

                rows_to_save.append([
                    group_name,
                    row["company"],
                    row["family"],
                    row["category"],
                    row["grade"],
                    row["location"],
                    row["price_point"],
                    row["delivery_location"]
                ])

            worksheet.append_rows(rows_to_save)
            read_data.read_groups_data.clear()
            st.success("Group saved successfully")

with tab_modify:

    spreadsheet, sheet_names = read_data.get_sheet_names(
        SPREADSHEET_URL
    )

    worksheet = spreadsheet.worksheet("Groups")

    group_df = pd.DataFrame(
        worksheet.get_all_records()
    )

    if group_df.empty:

        st.warning("No groups found")

    else:

        all_groups = sorted(
            group_df["group_name"].unique()
        )

        selected_group = st.selectbox(
            "Select Group",
            all_groups,
            key="modify_group_select"
        )

        selected_group_df = group_df[
            group_df["group_name"] == selected_group
        ].reset_index(drop=True)

        if "modify_rows" not in st.session_state:

            st.session_state.modify_rows = []

        if (
            st.session_state.modify_rows == []
            or st.session_state.get("loaded_group") != selected_group
        ):

            st.session_state.modify_rows = (
                selected_group_df[
                    [
                        "company",
                        "family",
                        "category",
                        "grade",
                        "location",
                        "price_point",
                        "delivery_location"
                    ]
                ]
                .to_dict("records")
            )

            st.session_state.loaded_group = selected_group

        with st.form("modify_group_form"):

            for i, row in enumerate(
                st.session_state.modify_rows
            ):

                cols = st.columns([1,1,1,1,1,1,1,0.4])

                row["company"] = cols[0].selectbox(
                    "Company",
                    utilities.COMPANIES,
                    index=(
                        utilities.COMPANIES.index(row["company"])
                        if row["company"] in utilities.COMPANIES
                        else 0
                    ),
                    key=f"{selected_group}_modify_company_{i}"
                )

                row["family"] = cols[1].selectbox(
                    "Family",
                    utilities.FAMILY,
                    index=(
                        utilities.FAMILY.index(row["family"])
                        if row["family"] in utilities.FAMILY
                        else 0
                    ),
                    key=f"{selected_group}_modify_family_{i}"
                )

                row["category"] = cols[2].selectbox(
                    "Category",
                    utilities.CATEGORY,
                    index=(
                        utilities.CATEGORY.index(row["category"])
                        if row["category"] in utilities.CATEGORY
                        else 0
                    ),
                    key=f"{selected_group}_modify_category_{i}"
                )

                row["grade"] = cols[3].text_input(
                    "Grade",
                    value=row["grade"],
                    key=f"{selected_group}_modify_grade_{i}"
                )

                row["location"] = cols[4].text_input(
                    "Location",
                    value=row["location"],
                    key=f"{selected_group}_modify_location_{i}"
                )

                available_price_points = utilities.PRICE_POINT_MAP.get(
                    row["company"],
                    []
                )

                row["price_point"] = cols[5].selectbox(
                    "Price Point",
                    available_price_points,
                    index=(
                        available_price_points.index(
                            row["price_point"]
                        )
                        if row["price_point"]
                        in available_price_points
                        else 0
                    ),
                    key=f"{selected_group}_modify_price_point_{i}"
                )

                if (
                    row["price_point"] == "Plant"
                    and row["company"]
                    in utilities.SPECIAL_FREIGHT_COMPANIES
                ):

                    row["delivery_location"] = (
                        cols[6].text_input(
                            "Delivery Location",
                            value=row.get(
                                "delivery_location",
                                ""
                            ),
                            key=f"{selected_group}_modify_delivery_{i}"
                        )
                    )

                else:

                    row["delivery_location"] = ""

                if cols[7].form_submit_button(
                    "❌",
                    key=f"modify_delete_{i}",
                    use_container_width=True
                ):

                    st.session_state.modify_rows.pop(i)

                    st.rerun()

            add_modify_clicked = st.form_submit_button(
                "➕ Add Row"
            )

            update_group_clicked = (
                st.form_submit_button(
                    "💾 Update Group"
                )
            )

            if add_modify_clicked:

                st.session_state.modify_rows.append(
                    {
                        "company": "",
                        "family": "",
                        "category": "",
                        "grade": "",
                        "location": "",
                        "price_point": "",
                        "delivery_location": ""
                    }
                )

                st.rerun()

            if update_group_clicked:

                # Delete old rows
                existing_records = (
                    worksheet.get_all_records()
                )

                filtered_records = [
                    row
                    for row in existing_records
                    if row["group_name"]
                    != selected_group
                ]

                worksheet.clear()

                worksheet.append_row([
                    "group_name",
                    "company",
                    "family",
                    "category",
                    "grade",
                    "location",
                    "price_point",
                    "delivery_location"
                ])

                if filtered_records:

                    worksheet.append_rows([
                        [
                            row["group_name"],
                            row["company"],
                            row["family"],
                            row["category"],
                            row["grade"],
                            row["location"],
                            row["price_point"],
                            row["delivery_location"]
                        ]
                        for row in filtered_records
                    ])

                updated_rows = []

                for row in st.session_state.modify_rows:

                    updated_rows.append([
                        selected_group,
                        row["company"],
                        row["family"],
                        row["category"],
                        row["grade"],
                        row["location"],
                        row["price_point"],
                        row["delivery_location"]
                    ])

                worksheet.append_rows(updated_rows)
                read_data.read_groups_data.clear()
                st.success(f"{selected_group} updated successfully")

                # st.rerun()

with tab_delete:

    spreadsheet, sheet_names = read_data.get_sheet_names(
        SPREADSHEET_URL
    )

    worksheet = spreadsheet.worksheet("Groups")

    group_df = pd.DataFrame(
        worksheet.get_all_records()
    )

    if group_df.empty:

        st.warning("No groups found")

    else:

        all_groups = sorted(
            group_df["group_name"].unique()
        )

        with st.form("delete_group_form"):

            selected_delete_group = st.selectbox(
                "Select Group to Delete",
                all_groups,
                key="delete_group_select"
            )

            st.warning(f"You are about to delete a Group.")

            confirm_delete = st.checkbox(
                "I confirm deletion",
                key="confirm_delete_group"
            )

            delete_clicked = st.form_submit_button(
                "🗑️ Delete Group"
            )

            if delete_clicked:

                if not confirm_delete:

                    st.error(
                        "Please confirm deletion first"
                    )

                else:

                    existing_records = (
                        worksheet.get_all_records()
                    )

                    filtered_records = [
                        row
                        for row in existing_records
                        if row["group_name"]
                        != selected_delete_group
                    ]

                    worksheet.clear()

                    worksheet.append_row([
                        "group_name",
                        "company",
                        "family",
                        "grade",
                        "location",
                        "price_point",
                        "delivery_location"
                    ])

                    if filtered_records:

                        worksheet.append_rows([
                            [
                                row["group_name"],
                                row["company"],
                                row["family"],
                                row["grade"],
                                row["location"],
                                row["price_point"],
                                row["delivery_location"]
                            ]
                            for row in filtered_records
                        ])
                    read_data.read_groups_data.clear()
                    st.success(
                        f"{selected_delete_group} deleted successfully"
                    )

                    # st.rerun()