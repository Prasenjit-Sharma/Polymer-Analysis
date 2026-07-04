import streamlit as st
import pandas as pd
import utilities

utilities.apply_common_styles("Compare Prices")

if "rows" not in st.session_state:
    st.session_state.rows = []
if "selected_group_df" not in st.session_state:
    st.session_state.selected_group_df = []



utilities.new_render_create_group()

with st.container(border=True):
    col1, col2, col3, col4, col5 = st.columns([1,1,1,1,1], vertical_alignment="bottom")
    with col1:
        price_date = st.date_input( "Price Date", format="DD/MM/YYYY")
    with col2:
        selected_qty = st.number_input("Quantity",min_value=0,max_value=9999)
    with col3:
        show_published = st.toggle("Published Discounts", value=True, key="frag_show_pub")
    with col4:
        show_unpublished = st.toggle("UnPublished Discounts", key="frag_show_unpub")

    with col5:
        submit_price = st.button("Get Prices",type="primary",width="stretch")

if submit_price:
    df = pd.DataFrame(st.session_state.rows)
    st.write(df)
    selected_family=df["family"]
    st.session_state.selected_group_df = df
    utilities.get_discounts(df, selected_family[0], selected_qty, price_date,
                             show_published, show_unpublished)
    utilities.pricing_editor_fragment()
    # utilities.render_interactive_pricing_zone(df)


