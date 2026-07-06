import streamlit as st
import utilities

utilities.display_market_metrics()

if "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = False

# Fetching data
with st.container(border=True):
    
    st.markdown("### Latest Polymer News")
    with st.spinner("Scanning for Polymer News..."):
        news_data = utilities.fetch_price_news()
    
    if news_data:
        # Display as Cards
        for news in news_data:
            with st.expander(f"📅 {news['Date']} | {news['Title']}", expanded=False):
                st.markdown(f"**Full Update:**")
                st.write(news['Details'])
    else:
        st.warning("No news items found")

