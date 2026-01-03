import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

st.title("Quantity Discount – Volume Slabs")

st.markdown(
    """
    Enter slabs as **Upto Volume + Discount Amount**  
    (From-volume is automatically derived from the previous slab)
    """
)

# -----------------------------
# Initial empty structure
# -----------------------------
default_df = pd.DataFrame(
    {
        "Upto Volume": [100],
        "Discount Amount": [0.0],
    }
)

# -----------------------------
# Editable table
# -----------------------------
slab_df = st.data_editor(
    default_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Upto Volume": st.column_config.NumberColumn(
            min_value=1,
            step=1,
            format="%d",
            required=True
        ),
        "Discount Amount": st.column_config.NumberColumn(
            min_value=0.0,
            step=1.0,
            format="₹ %.2f",
            required=True
        ),
    },
)

# -----------------------------
# Submit
# -----------------------------
if st.button("Save Quantity Discount"):
    if slab_df.empty:
        st.error("At least one slab is required.")
        st.stop()

    # Validate ordering
    volumes = slab_df["Upto Volume"].tolist()
    if volumes != sorted(volumes):
        st.error("Upto Volume must be in increasing order.")
        st.stop()

    # Build final structure
    quantity_slabs = []
    for _, row in slab_df.iterrows():
        quantity_slabs.append(
            {
                "upto_volume": int(row["Upto Volume"])
                if not pd.isna(row["Upto Volume"])
                else None,
                "amount": float(row["Discount Amount"]),
            }
        )

    st.success("Quantity discount slabs saved successfully")
    st.json(quantity_slabs)
