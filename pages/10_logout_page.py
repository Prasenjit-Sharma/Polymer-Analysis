import streamlit as st

st.title("🚪 Logout")

st.write(f"**Logged in as:** {st.session_state.get('username', 'User')}")

st.markdown("---")

st.write("Are you sure you want to logout?")

col1, col2, col3 = st.columns([1, 1, 3])

with col1:
    if st.button("✅ Yes, Logout", type="primary", width="stretch"):
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

with col2:
    if st.button("❌ Cancel", width="stretch"):
        st.switch_page("pages/1_home_dash.py")