import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from sqlalchemy import create_engine


# connection
from sqlalchemy import create_engine

engine = create_engine(
    "mssql+pyodbc://@SAHIL\\SQLEXPRESS/rec_sys?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
)



# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(page_title="Dashboard", layout="wide")
st.title("Revenue Growth & Personalization Analytics Dashboard")

# --------------------------------------------------
# SEGMENT COLOR PALETTE
# --------------------------------------------------

SEG_COL = {
    "High-value loyal customers": "#3b82f6",
    "At-risk customers":          "#ef4444",
    "New buyers":                 "#10b981",
    "Price-sensitive users":      "#f59e0b",
}
SEG_ORDER = [
    "High-value loyal customers",
    "At-risk customers",
    "New buyers",
    "Price-sensitive users",
]

# --------------------------------------------------
# PRICE BAND DEFINITIONS
# --------------------------------------------------

PRICE_BANDS = ["Budget ($0-$25)", "Mid-Range ($25-$75)", "Premium ($75-$150)", "Luxury ($150+)"]

def assign_price_band(price):
    if price < 25:
        return "Budget ($0-$25)"
    elif price < 75:
        return "Mid-Range ($25-$75)"
    elif price < 150:
        return "Premium ($75-$150)"
    else:
        return "Luxury ($150+)"

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

# @st.cache_data
# def load_data():
#     orders          = pd.read_csv("orders_clean.csv")
#     order_items     = pd.read_csv("order_items_clean.csv")
#     products        = pd.read_csv("products_clean.csv")
#     customer_feat   = pd.read_csv("customer_segment_mapping.csv")
#     recommendations = pd.read_csv("recommended_products.csv")
#     forecast        = pd.read_csv("sales_forecast.csv")
#     customers       = pd.read_csv("customers_clean.csv")






@st.cache_data
def load_data():

    orders          = pd.read_sql("SELECT * FROM orders_clean", engine)
    order_items     = pd.read_sql("SELECT * FROM order_items_clean", engine)
    products        = pd.read_sql("SELECT * FROM products_clean", engine)
    customer_feat   = pd.read_sql("SELECT * FROM customer_segment_mapping", engine)
    recommendations = pd.read_sql("SELECT * FROM recommended_products", engine)
    forecast        = pd.read_sql("SELECT * FROM sales_forecast", engine)
    customers       = pd.read_sql("SELECT * FROM customers_clean", engine)

    # preprocessing
    orders["order_time"] = pd.to_datetime(orders["order_time"])
    forecast["ds"]       = pd.to_datetime(forecast["ds"])

    if "product_name" not in products.columns:
        products.rename(columns={"name": "product_name"}, inplace=True)

    seg_lookup = (
        customer_feat[["customer_id", "segment"]]
        .drop_duplicates("customer_id")
        .query("segment not in ['Regular customers', '0']")
    )

    return orders, order_items, products, seg_lookup, recommendations, forecast, customers


orders, order_items, products, seg_lookup, recommendations, forecast, customers_df = load_data()



# --------------------------------------------------
# BUILD SALES TABLE
# --------------------------------------------------

sales = pd.merge(order_items, orders, on="order_id", how="left")
sales = pd.merge(sales, products, on="product_id", how="left")
sales["line_subtotal"] = sales["quantity"] * sales["unit_price_usd"]
order_subtotals        = sales.groupby("order_id")["line_subtotal"].transform("sum")
sales["revenue"]       = sales["line_subtotal"] * (sales["total_usd"] / order_subtotals)

# Assign price band to every row based on unit_price_usd
sales["price_band"] = sales["unit_price_usd"].apply(assign_price_band)

# --------------------------------------------------
# FILTER OPTIONS
# --------------------------------------------------

default_start  = sales["order_time"].min().date()
default_end    = sales["order_time"].max().date()
all_countries  = sorted(sales["country"].dropna().unique().tolist())
all_categories = sorted(sales["category"].dropna().unique().tolist())
all_segments   = sorted(seg_lookup["segment"].dropna().unique().tolist())
all_bands      = PRICE_BANDS  # keep defined order

# --------------------------------------------------
# SESSION STATE INITIALISATION
# --------------------------------------------------

if "f_date_from"   not in st.session_state: st.session_state["f_date_from"]   = default_start
if "f_date_to"     not in st.session_state: st.session_state["f_date_to"]     = default_end
if "f_countries"   not in st.session_state: st.session_state["f_countries"]   = all_countries
if "f_categories"  not in st.session_state: st.session_state["f_categories"]  = all_categories
if "f_segments"    not in st.session_state: st.session_state["f_segments"]    = all_segments
if "f_price_bands" not in st.session_state: st.session_state["f_price_bands"] = all_bands

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.header("Filters")

if st.sidebar.button("Reset"):
    for k in ["f_date_from", "f_date_to", "f_countries", "f_categories", "f_segments", "f_price_bands"]:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

date_from = st.sidebar.date_input("Date From", key="f_date_from")
date_to   = st.sidebar.date_input("Date To",   key="f_date_to")

# Country
st.sidebar.markdown("**Country**")
cc1, cc2 = st.sidebar.columns(2)
if cc1.button("All",   key="btn_country_all"):
    st.session_state["f_countries"] = all_countries
    st.rerun()
if cc2.button("Clear", key="btn_country_clr"):
    st.session_state["f_countries"] = []
    st.rerun()
country_filter = st.sidebar.multiselect(
    "Countries", options=all_countries,
    key="f_countries", label_visibility="collapsed",
)

# Category
st.sidebar.markdown("**Category**")
ca1, ca2 = st.sidebar.columns(2)
if ca1.button("All",   key="btn_cat_all"):
    st.session_state["f_categories"] = all_categories
    st.rerun()
if ca2.button("Clear", key="btn_cat_clr"):
    st.session_state["f_categories"] = []
    st.rerun()
category_filter = st.sidebar.multiselect(
    "Categories", options=all_categories,
    key="f_categories", label_visibility="collapsed",
)

# Customer Segment
st.sidebar.markdown("**Customer Segment**")
cs1, cs2 = st.sidebar.columns(2)
if cs1.button("All",   key="btn_seg_all"):
    st.session_state["f_segments"] = all_segments
    st.rerun()
if cs2.button("Clear", key="btn_seg_clr"):
    st.session_state["f_segments"] = []
    st.rerun()
segment_filter = st.sidebar.multiselect(
    "Segments", options=all_segments,
    key="f_segments", label_visibility="collapsed",
)

# Price Band
st.sidebar.markdown("**Price Band**")
pb1, pb2 = st.sidebar.columns(2)
if pb1.button("All",   key="btn_pb_all"):
    st.session_state["f_price_bands"] = all_bands
    st.rerun()
if pb2.button("Clear", key="btn_pb_clr"):
    st.session_state["f_price_bands"] = []
    st.rerun()
price_band_filter = st.sidebar.multiselect(
    "Price Bands",
    options=all_bands,
    key="f_price_bands",
    label_visibility="collapsed",
    help="Filter orders by unit price tier:\n- Budget < $25\n- Mid-Range $25-$75\n- Premium $75-$150\n- Luxury $150+",
)

# --------------------------------------------------
# GUARD: stop if any filter is empty
# --------------------------------------------------

if not country_filter:
    st.warning("No country selected. Please select at least one.")
    st.stop()
if not category_filter:
    st.warning("No category selected. Please select at least one.")
    st.stop()
if not segment_filter:
    st.warning("No segment selected. Please select at least one.")
    st.stop()
if not price_band_filter:
    st.warning("No price band selected. Please select at least one.")
    st.stop()

# --------------------------------------------------
# APPLY FILTERS
# --------------------------------------------------

filtered = sales.copy()
filtered = filtered[
    (filtered["order_time"].dt.date >= date_from) &
    (filtered["order_time"].dt.date <= date_to)
]
filtered = filtered[filtered["country"].isin(country_filter)]
filtered = filtered[filtered["category"].isin(category_filter)]
filtered = filtered[filtered["price_band"].isin(price_band_filter)]   # price band filter

seg_customers = seg_lookup[seg_lookup["segment"].isin(segment_filter)]["customer_id"]
filtered      = filtered[filtered["customer_id"].isin(seg_customers)]

# --------------------------------------------------
# KPI METRICS
# --------------------------------------------------

st.subheader("Business KPIs")
k1, k2, k3, k4, k5 = st.columns(5)

revenue                = filtered.drop_duplicates("order_id")["total_usd"].sum()
orders_count           = filtered["order_id"].nunique()
total_customers        = len(customers_df)
active_customers_count = filtered["customer_id"].nunique()
aov                    = revenue / orders_count if orders_count > 0 else 0

k1.metric("Total Revenue",    f"${revenue:,.2f}")
k2.metric("Total Orders",     f"{orders_count:,}")
k3.metric("Total Customers",  f"{total_customers:,}")
k4.metric("Active Customers", f"{active_customers_count:,}")
k5.metric("Avg Order Value",  f"${aov:,.2f}")


# --------------------------------------------------
# TABS
# --------------------------------------------------

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Sales Forecast", "Customer Segments",
    "Customer Intelligence", "Top Products & Revenue", "Business Insights",
])

# ======================================================
# TAB 1 - SALES FORECAST
# ======================================================

with tab1:

    st.subheader("Sales Forecast Overview")

    ctrl1, _, _ = st.columns([2, 1, 1])
    with ctrl1:
        horizon_days = st.selectbox(
            "Forecast Horizon",
            [("30 days", 30), ("60 days", 60), ("90 days", 90)],
            format_func=lambda x: x[0],
        )[1]

    fc          = forecast.sort_values("ds").copy()
    fc["upper"] = fc["yhat"] * 1.08
    fc["lower"] = fc["yhat"] * 0.92
    split       = len(fc) - horizon_days
    fc_hist     = fc.iloc[:split] if split > 0 else fc
    fc_future   = fc.iloc[split:] if split > 0 else pd.DataFrame()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=fc_hist["ds"], y=fc_hist["yhat"], mode="lines", name="Historical",
    ))
    if len(fc_future) > 0:
        fig.add_trace(go.Scatter(
            x=pd.concat([fc_future["ds"], fc_future["ds"][::-1]]),
            y=pd.concat([fc_future["upper"], fc_future["lower"][::-1]]),
            fill="toself", fillcolor="rgba(255,0,0,0.1)",
            line=dict(color="rgba(255,255,255,0)"), name="Confidence Band",
        ))
        fig.add_trace(go.Scatter(
            x=fc_future["ds"], y=fc_future["yhat"],
            mode="lines", line=dict(color="red", dash="dash"), name="Forecast",
        ))
    fig.update_layout(xaxis_title="Date", yaxis_title="Revenue ($)", height=400)
    st.plotly_chart(fig, use_container_width=True)

    fv = fc_future["yhat"].values if len(fc_future) > 0 else np.array([0])
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Projected Revenue",   f"${fv.sum():,.0f}")
    m2.metric("Avg Daily Revenue",   f"${fv.mean():,.0f}")
    m3.metric("Peak Forecast Day",   f"${fv.max():,.0f}")
    m4.metric("Lowest Forecast Day", f"${fv.min():,.0f}")

    st.divider()

    

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Revenue by Country")
        country_rev = (
            filtered.drop_duplicates("order_id")
            .groupby("country")["total_usd"].sum()
            .reset_index()
            .rename(columns={"total_usd": "revenue"})
            .sort_values("revenue", ascending=True)
        )
        fig_country = px.bar(
            country_rev, x="revenue", y="country", orientation="h",
            labels={"revenue": "Revenue ($)", "country": "Country"},
        )
        st.plotly_chart(fig_country, use_container_width=True)

    with col2:
        st.subheader("Revenue Trend")
        grp = st.radio("Group By", ["Day", "Month", "Quarter", "Year"], horizontal=True)
        temp = filtered.drop_duplicates("order_id").copy()
        if grp == "Month":
            temp["period"] = temp["order_time"].dt.to_period("M").astype(str)
        elif grp == "Quarter":
            temp["period"] = temp["order_time"].dt.to_period("Q").astype(str)
        elif grp == "Day":
            temp["period"] = temp["order_time"].dt.to_period("D").astype(str)
        else:
            temp["period"] = temp["order_time"].dt.year.astype(str)
        trend = (
            temp.groupby("period")["total_usd"].sum()
            .reset_index().rename(columns={"total_usd": "revenue"})
        )
        fig_trend = px.bar(
            trend, x="period", y="revenue",
            labels={"revenue": "Revenue ($)", "period": "Period"},
        )
        st.plotly_chart(fig_trend, use_container_width=True)


# ======================================================
# TAB 2 - CUSTOMER SEGMENTS
# ======================================================

with tab2:

    st.subheader("Customer Segment Distribution")

    active_cust_ids = filtered["customer_id"].unique()

    seg_counts = (
        seg_lookup[seg_lookup["customer_id"].isin(active_cust_ids)]
        .groupby("segment")["customer_id"].nunique()
        .reset_index().rename(columns={"customer_id": "customers"})
    )

    seg_counts["segment"] = pd.Categorical(
        seg_counts["segment"], categories=SEG_ORDER, ordered=True
    )
    seg_counts = seg_counts.sort_values("segment").dropna(subset=["segment"])

    fig_pie = px.pie(
        seg_counts,
        names="segment",
        values="customers",
        title="Customers by Segment",
        color="segment",
        color_discrete_map=SEG_COL,
        category_orders={"segment": SEG_ORDER},
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    # Price Band Mix by Segment
    st.subheader("Revenue by Customer Segment")
    seg_band = (
        filtered.merge(seg_lookup, on="customer_id", how="left")
        .dropna(subset=["segment"])
        .groupby(["segment", "price_band"])["revenue"]
        .sum()
        .reset_index()
    )



    st.divider()

    st.subheader("Customers by Selected Segment")

    customers_segment = seg_lookup[seg_lookup["customer_id"].isin(active_cust_ids)]
    customers_segment = pd.merge(customers_segment, customers_df, on="customer_id", how="left")

    if "name" not in customers_segment.columns:
        if "first_name" in customers_segment.columns and "last_name" in customers_segment.columns:
            customers_segment["name"] = customers_segment["first_name"] + " " + customers_segment["last_name"]

    cols = ["customer_id", "name", "email", "country", "age", "segment"]
    cols = [c for c in cols if c in customers_segment.columns]

    st.dataframe(
        customers_segment[cols].sort_values("segment"),
        use_container_width=True
    )

    st.divider()

    st.subheader("Revenue by Segment")

    seg_rev = (
        filtered.drop_duplicates("order_id")[["order_id", "customer_id", "total_usd"]]
        .merge(seg_lookup, on="customer_id", how="left")
        .dropna(subset=["segment"])
        .groupby("segment")["total_usd"].sum()
        .reset_index().rename(columns={"total_usd": "revenue"})
        .sort_values("revenue", ascending=False)
    )

    fig_seg = go.Figure()
    for seg in SEG_ORDER:
        sub = seg_rev[seg_rev["segment"] == seg]
        if sub.empty:
            continue
        fig_seg.add_trace(go.Bar(
            x=sub["segment"],
            y=sub["revenue"],
            name=seg,
            marker_color=SEG_COL.get(seg, "#94a3b8"),
        ))

    fig_seg.update_layout(
        barmode="group",
        title="Revenue by Segment",
        xaxis_title="Segment",
        yaxis_title="Revenue ($)",
        showlegend=True,
    )

    st.plotly_chart(fig_seg, use_container_width=True)

    st.subheader("Customers Contributing to Revenue by Segment")

    customer_revenue = (
        filtered.groupby("customer_id")["revenue"]
        .sum()
        .reset_index()
    )

    customer_revenue = pd.merge(customer_revenue, seg_lookup, on="customer_id", how="left")
    customer_revenue = pd.merge(customer_revenue, customers_df, on="customer_id", how="left")

    if "name" not in customer_revenue.columns:
        if "first_name" in customer_revenue.columns and "last_name" in customer_revenue.columns:
            customer_revenue["name"] = customer_revenue["first_name"] + " " + customer_revenue["last_name"]

    cols_rev = ["customer_id", "name", "email", "country", "age", "segment", "revenue"]
    cols_rev = [c for c in cols_rev if c in customer_revenue.columns]

    customer_revenue = customer_revenue.sort_values("revenue", ascending=False)
    st.dataframe(customer_revenue[cols_rev], use_container_width=True)

    st.divider()
    st.subheader("Repeated Customers")

    repeat_orders = (
        filtered.groupby("customer_id")["order_id"]
        .nunique()
        .reset_index()
        .rename(columns={"order_id": "order_count"})
    )

    repeat_customers = repeat_orders[repeat_orders["order_count"] > 1]
    repeat_customers = pd.merge(repeat_customers, seg_lookup, on="customer_id", how="left")
    repeat_customers = pd.merge(repeat_customers, customers_df, on="customer_id", how="left")

    if "name" not in repeat_customers.columns:
        if "first_name" in repeat_customers.columns and "last_name" in repeat_customers.columns:
            repeat_customers["name"] = repeat_customers["first_name"] + " " + repeat_customers["last_name"]

    cols_rep = ["customer_id", "name", "email", "country", "age", "segment", "order_count"]
    cols_rep = [c for c in cols_rep if c in repeat_customers.columns]

    repeat_customers = repeat_customers.sort_values(by="order_count", ascending=False)

    st.metric("Total Repeat Customers", len(repeat_customers))
    st.dataframe(repeat_customers[cols_rep], use_container_width=True)


# ======================================================
# TAB 3 - CUSTOMER INTELLIGENCE
# ======================================================

with tab3:

    st.subheader("Customer 360 View")

    customer_list     = sorted(customers_df["customer_id"].unique())
    selected_customer = st.selectbox("Select Customer ID", customer_list)

    customer_info = customers_df[customers_df["customer_id"] == selected_customer]

    rfm_df   = pd.read_csv("customer_segment_mapping.csv")
    rfm_info = rfm_df[rfm_df["customer_id"] == selected_customer]

    if not rfm_info.empty:
        r   = int(rfm_info["recency"].values[0])
        f   = int(rfm_info["frequency"].values[0])
        m   = float(rfm_info["monetary"].values[0])
        seg = rfm_info["segment"].values[0]

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Recency (days)", r)
        k2.metric("Frequency", f)
        k3.metric("Monetary ($)", f"${m:,.2f}")
        k4.metric("Segment", seg)
    else:
        st.warning("No RFM data available for this customer.")

    st.divider()

    st.subheader("Customer Details")
    if not customer_info.empty:
        st.dataframe(
            customer_info.drop(columns=["signup_date", "marketing_opt_in"], errors="ignore"),
            use_container_width=True,
        )
    else:
        st.warning("Customer details not found.")

    


    st.subheader("Recommended Products")

    recs = recommendations[recommendations["customer_id"] == selected_customer]
    recs_enriched = pd.merge(
        recs,
        products[["product_id", "product_name", "category"]],
        left_on="recommended_product",
        right_on="product_id",
        how="left",
    ).drop(columns=["product_id"], errors="ignore")

    if not recs_enriched.empty:
        st.dataframe(recs_enriched, use_container_width=True)
    else:
        st.info("No recommendations available for this customer.")

    st.subheader("Customer Purchase History")

    history = filtered[filtered["customer_id"] == selected_customer]

    if not history.empty:
        hist_summary = (
            history.groupby("product_name")["revenue"]
            .sum()
            .reset_index()
            .sort_values("revenue", ascending=False)
            .head(10)
        )

        fig_hist = px.bar(
            hist_summary,
            x="product_name",
            y="revenue",
            title="Top Purchased Products",
        )
        fig_hist.update_layout(xaxis_tickangle=-35)
        st.plotly_chart(fig_hist, use_container_width=True)
    else:
        st.info("No purchase history available for this customer.")


# ======================================================
# TAB 4 - TOP PRODUCTS & CATEGORIES
# ======================================================

with tab4:

    st.subheader("Top 10 Revenue Products")

    # 🔥 Dynamic Top Products (based on ALL filters including date)
    top_products = (
        filtered.groupby("product_name")["revenue"]
        .sum()
        .reset_index()
        .sort_values("revenue", ascending=False)
        .head(10)
    )

    fig_prod = px.bar(
        top_products,
        x="product_name",
        y="revenue",
        labels={"revenue": "Revenue ($)", "product_name": "Product"},
        title="Top 10 Products by Revenue",
    )
    fig_prod.update_layout(xaxis_tickangle=-35)

    st.plotly_chart(fig_prod, use_container_width=True)


    # ======================================================
    # ✅ Revenue by Price Band (Fully Dynamic)
    # ======================================================

    st.subheader("Revenue by Price Band")

    band_rev = (
        filtered.groupby("price_band")["revenue"]
        .sum()
        .reset_index()
    )

    # Ensure correct order
    band_rev["price_band"] = pd.Categorical(
        band_rev["price_band"],
        categories=PRICE_BANDS,
        ordered=True
    )

    band_rev = band_rev.sort_values("price_band")

    fig_band = px.bar(
        band_rev,
        x="price_band",
        y="revenue",
        color="price_band",
        labels={"price_band": "Price Band", "revenue": "Revenue ($)"},
        title="Revenue by Price Band",
        color_discrete_sequence=["#10b981", "#3b82f6", "#f59e0b", "#ef4444"],
        category_orders={"price_band": PRICE_BANDS},
    )

    fig_band.update_layout(showlegend=False)

    st.plotly_chart(fig_band, use_container_width=True)


    # ======================================================
    # ✅ Revenue by Category
    # ======================================================

    st.subheader("Revenue by Category")

    cat_rev = (
        filtered.groupby("category")["revenue"]
        .sum()
        .reset_index()
        .sort_values("revenue", ascending=False)
    )

    fig_cat = px.bar(
        cat_rev,
        x="category",
        y="revenue",
        color="category",
        labels={"revenue": "Revenue ($)", "category": "Category"},
        title="Revenue by Category",
    )

    st.plotly_chart(fig_cat, use_container_width=True)


# ======================================================
# TAB 5 - BUSINESS INSIGHTS
# ======================================================

with tab5:

    orders_dedup = filtered.drop_duplicates("order_id")
    top_country  = orders_dedup.groupby("country")["total_usd"].sum().idxmax()
    top_product  = filtered.groupby("product_name")["revenue"].sum().idxmax()
    top_category = filtered.groupby("category")["revenue"].sum().idxmax()
    best_segment = (
        filtered.drop_duplicates("order_id")[["order_id", "customer_id", "total_usd"]]
        .merge(seg_lookup, on="customer_id", how="left")
        .dropna(subset=["segment"])
        .groupby("segment")["total_usd"].sum().idxmax()
    )
    temp          = orders_dedup.copy()
    temp["month"] = temp["order_time"].dt.to_period("M").astype(str)
    monthly       = temp.groupby("month")["total_usd"].sum()
    growth        = monthly.pct_change().mean() * 100

    best_band = (
        filtered.groupby("price_band")["revenue"].sum().idxmax()
        if not filtered.empty else "N/A"
    )

    band_share = (
        filtered.groupby("price_band")["revenue"].sum()
        .reindex(PRICE_BANDS).fillna(0)
    )
    total_rev = band_share.sum()
    band_pct  = (band_share / total_rev * 100).round(1) if total_rev > 0 else band_share

    st.markdown(f"""
### Key Insights

**Top Revenue Country:** {top_country}

**Top Performing Product:** {top_product}

**Top Revenue Category:** {top_category}

**Highest Revenue Segment:** {best_segment}

**Top Price Band:** {best_band}

**Average Monthly Growth:** {growth:.2f}%
""")

    