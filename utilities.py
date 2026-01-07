from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import pandas as pd
import plotly.express as px

FISCAL_START = 4

month_order = ["January", "February", "March", "April", "May", "June", 
               "July", "August", "September", "October", "November", "December"]

def latest_data (df):
    display_year = df.iloc[-1]['Year']
    display_month = df.iloc[-1]['Month Name']
    display_month_no = month_order.index(display_month)+1
    return display_year,display_month,display_month_no


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

def draw_pie(df, values, names, title):
    fig = px.pie(df, values=values,names = names, title=title)
    fig.update_traces(texttemplate='<b>%{label}</b>: <br>%{value:.0f} (%{percent:.1%})')
    fig.update_layout(showlegend=False)
    return fig

def draw_sunburst(df,path,values,title):
    fig = px.sunburst(df, path=path, values=values, title=title)
    return fig

def draw_histogram_month_quantity(df, color, title):
    fig = px.histogram(
            df.sort_values(by='Month Name'),
            x="Month Name",
            y="Quantity",
            # pattern_shape="Material Group",
            color=color,
            title=title,
            # barmode="group", # Groups the bars side-by-side
            category_orders={"Month Name": month_order},
            text_auto=True
            )
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
    fig.update_layout(xaxis_title="",yaxis_title="")
    return fig

def draw_histogram_bar(df,x,y,color):
    fig = px.histogram(df, x=x, y=y,
                    color=color, barmode='group',text_auto=True)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom",y=-0.4,xanchor="center"))
    fig.update_layout(xaxis_title="",yaxis_title="")
    return fig
