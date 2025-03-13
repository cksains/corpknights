#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 28 15:49:45 2025
Edited on Thu Mar 13 21:30:30 2025

@author: chloesainsbury
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.colors as pc
import plotly.express as px

# Load the CSV file
csv_file_path = "sei_summary_1.csv"
df_summary = pd.read_csv(csv_file_path)

# --- Standardize Column Names ---
column_rename_map = {}
for year in ["2019", "2020", "2021", "2022", "2023"]:
    column_rename_map[f"{year} Sustainable Revenue Ratio"] = f"{year[-2:]}SRR"
    column_rename_map[f"{year} Sustainable Investment Ratio"] = f"{year[-2:]}SIR"
    column_rename_map[f"{year} Total Revenue, USD (PPP) Millions"] = f"{year[-2:]}REV"
    column_rename_map[f"{year} Total Investment, USD (PPP) Millions"] = f"{year[-2:]}INV"
    column_rename_map[f"{year} Sustainable Revenue, USD (PPP) Millions"] = f"{year[-2:]}SRV"
    column_rename_map[f"{year} Sustainable Investment, USD (PPP) Millions"] = f"{year[-2:]}SIV"

df_summary.rename(columns=column_rename_map, inplace=True)

# --- Define Metrics ---
metric_columns = {
    "Revenue (R) (USD Millions)": [f"{year}REV" for year in ["19", "20", "21", "22", "23"]],
    "Investment (I) (USD Millions)": [f"{year}INV" for year in ["19", "20", "21", "22", "23"]],
    "Sustainable Revenue (SR) (USD Millions)": [f"{year}SRV" for year in ["19", "20", "21", "22", "23"]],
    "Sustainable Investment (SI) (USD Millions)": [f"{year}SIV" for year in ["19", "20", "21", "22", "23"]],
    "Sustainable Revenue Ratio (SRR) (Ratio)": [f"{year}SRR" for year in ["19", "20", "21", "22", "23"]],
    "Sustainable Investment Ratio (SIR) (Ratio)": [f"{year}SIR" for year in ["19", "20", "21", "22", "23"]],
}

st.set_page_config(layout="wide")

# --- 🌍 DATASET FILTERS ---
st.sidebar.header("🌍 Dataset Filters")
st.sidebar.write("🔹 These filters adjust the dataset before visualization.")

# Universe Selection
universe_toggle = st.sidebar.radio("Select Universe (Affects Available Years)", 
                                   ["4-Year Universe", "5-Year Universe", "Complete Universe"])

# Adjust Available Years Based on Selection
valid_years = ["19", "20", "21", "22"]
if universe_toggle in ["5-Year Universe", "Complete Universe"]:
    valid_years.append("23")  # Only allow 2023 if "5-Year" or "Complete" is selected

# CKPG Selection
selected_ckpgs = st.sidebar.multiselect(
    "Select CKPG(s) (Affects Table & Chart)", 
    sorted(df_summary["CKPG"].dropna().unique()),  
    default=sorted(df_summary["CKPG"].dropna().unique())[:2]
)

if not selected_ckpgs:
    st.warning("⚠ Please select at least one CKPG!")
    st.stop()

# --- Apply Filters to Dataset ---
df_filtered = df_summary[df_summary["CKPG"].isin(selected_ckpgs)].copy()

# ✅ Filter Metric Columns Based on Universe Selection
filtered_metric_columns = {
    key: [col for col in metric_columns[key] if col[:2] in valid_years]  
    for key in metric_columns
}
available_metrics = sum(filtered_metric_columns.values(), [])  # Flatten list

# ✅ Ensure CKPG, Name, and Country are always selectable
categorical_columns = ["CKPG", "Name", "Country"]

# ✅ Merge categorical and numeric columns
available_table_columns = categorical_columns + available_metrics

selected_columns = st.sidebar.multiselect(
    "Choose Columns to Display (Table Only)", 
    available_table_columns,  
    default=["CKPG", "Name"] + [col for col in available_metrics if "REV" in col][:1]
)

# ✅ Ensure we only allow sorting by numeric metrics
numeric_sortable_columns = [col for col in selected_columns if col not in categorical_columns]

# ✅ Ensure there's at least one valid metric for sorting
sort_column = st.sidebar.selectbox("Sort table by:", numeric_sortable_columns) if numeric_sortable_columns else "19REV"

# ✅ If too many values are missing, fall back to another column
if df_filtered[sort_column].isna().sum() > len(df_filtered) * 0.8:  # If >80% missing
    fallback_column = next((col for col in numeric_sortable_columns if df_filtered[col].notna().sum() > len(df_filtered) * 0.5), "19REV")
    st.warning(f"⚠️ Too many missing values in {sort_column}. Sorting by {fallback_column} instead.")
    sort_column = fallback_column


# --- 📊 DATA DISPLAY SETTINGS ---
st.sidebar.divider()
st.sidebar.header("📊 Data Display Settings")

top_x = st.sidebar.slider("Select Top X Companies", min_value=5, max_value=50, value=10)
exclude_rows = st.sidebar.multiselect("Exclude Companies", df_filtered["Name"].unique())

# ✅ Remove rows with missing sorting values before sorting
df_filtered = df_filtered.dropna(subset=[sort_column])  
df_filtered = df_filtered[~df_filtered["Name"].isin(exclude_rows)]  # Apply exclusions

# ✅ Sort before selecting top X companies
df_table = df_filtered.sort_values(by=sort_column, ascending=False, na_position="last").head(top_x)

# ✅ Display the logic in the UI
st.write(f"**🔍 Showing the top {top_x} companies sorted by {sort_column}**")

# --- 🛠 INTERACTIVE TABLE ---
st.data_editor(df_table[selected_columns].reset_index(drop=True), 
               height=500, use_container_width=True, column_config={col: {"sortable": True} for col in df_table[selected_columns].columns})

# --- 📈 CHART SETTINGS ---
st.sidebar.divider()
st.sidebar.header("📈 Chart Settings")

chart_type = st.sidebar.selectbox("Choose a Chart Type", ["Bar", "Line", "Scatter", "Box Plot"])
x_axis = st.sidebar.selectbox("X-Axis (Grouping)", ["CKPG", "Name", "Country"])

# --- Ensure only valid Y-axis metrics are selected ---
available_numeric_columns = [col for col in df_filtered.columns if col in sum(filtered_metric_columns.values(), [])]


selected_y_axes = st.sidebar.multiselect(
    "Y-Axis (Values to Compare)", 
    available_numeric_columns,  # Ensures only valid columns appear
    default=[col for col in available_numeric_columns if col.endswith("SRR")][:1]  # Default to an available metric
)

# Ensure only valid selected metrics exist in df_chart before melting
valid_y_axes = [col for col in selected_y_axes if col in df_filtered.columns]


# Stop execution if no valid Y-axis metrics
if not valid_y_axes:
    st.warning("⚠ No valid Y-axis metrics available for charting. Please check your filters or metric selections.")
    st.stop()

if selected_y_axes:
    df_chart = df_table.copy()  # Use the full filtered dataset, not just the table

    st.sidebar.write("### Sort Chart Data")
    chart_sort_column = st.sidebar.selectbox("Sort chart by:", selected_y_axes)
    
    chart_sort_order = st.sidebar.radio("Sorting Order:", ["Descending", "Ascending"])
    
    df_chart = df_chart.sort_values(by=chart_sort_column, ascending=(chart_sort_order == "Ascending"), na_position="last")

    df_melted = df_chart.melt(id_vars=["CKPG", "Name", "Country"], value_vars=valid_y_axes, var_name="Metric", value_name="Value")

    fig = px.bar(df_melted, x=x_axis, y="Value", color="Metric", barmode="group") if chart_type == "Bar" else \
          px.line(df_melted, x=x_axis, y="Value", color="Metric", markers=True) if chart_type == "Line" else \
          px.scatter(df_melted, x=x_axis, y="Value", color="Metric", size_max=10) if chart_type == "Scatter" else \
          px.box(df_melted, x=x_axis, y="Value", color="Metric")

    fig.update_layout(xaxis_title=x_axis, yaxis_title="Metric Value", xaxis=dict(type="category"))
    st.plotly_chart(fig, use_container_width=True)

#%%
