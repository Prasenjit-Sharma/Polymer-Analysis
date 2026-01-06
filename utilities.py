from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import pandas as pd

FISCAL_START = 4

def enforce_string_ids(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r"\.0$", "", regex=True)
                .str.strip()
            )
    return df

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