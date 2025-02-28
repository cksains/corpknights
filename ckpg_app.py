#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 28 15:49:45 2025

@author: chloesainsbury
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.colors as pc

# Load the CSV file
csv_file_path = "sei_summary_1.csv"
df_summary = pd.read_csv(csv_file_path)

# Standardizing column names
column_rename_map = {}
for year in ["2019", "2020", "2021", "2022", "2023"]:
    column_rename_map[f"{year} Sustainable Revenue Ratio"] = f"{year[-2:]}SRR"
    column_rename_map[f"{year} Sustainable Investment Ratio"] = f"{year[-2:]}SIR"
    column_rename_map[f"{year} Total Revenue, USD (PPP) Millions"] = f"{year[-2:]}REV"
    column_rename_map[f"{year} Total Investment, USD (PPP) Millions"] = f"{year[-2:]}INV"
    column_rename_map[f"{year} Sustainable Revenue, USD (PPP) Millions"] = f"{year[-2:]}SRV"
    column_rename_map[f"{year} Sustainable Investment, USD (PPP) Millions"] = f"{year[-2:]}SIV"

df_summary.rename(columns=column_rename_map, inplace=True)

# Define CKPG-relevant variables with units
metric_columns = {
    "Revenue (R) (USD Millions)": [f"{year}REV" for year in ["19", "20", "21", "22", "23"]],
    "Investment (I) (USD Millions)": [f"{year}INV" for year in ["19", "20", "21", "22", "23"]],
    "Sustainable Revenue (SR) (USD Millions)": [f"{year}SRV" for year in ["19", "20", "21", "22", "23"]],
    "Sustainable Investment (SI) (USD Millions)": [f"{year}SIV" for year in ["19", "20", "21", "22", "23"]],
    "Sustainable Revenue Ratio (SRR) (Ratio)": [f"{year}SRR" for year in ["19", "20", "21", "22", "23"]],
    "Sustainable Investment Ratio (SIR) (Ratio)": [f"{year}SIR" for year in ["19", "20", "21", "22", "23"]],
}

# Sidebar Filters
st.sidebar.header("Filters")
selected_ckpgs = st.sidebar.multiselect(
    "Select CKPG(s)", df_summary["CKPG"].dropna().unique(), 
    default=df_summary["CKPG"].unique()[:3]
)
universe_toggle = st.sidebar.radio("Select Universe:", ["4-Year Universe", "5-Year Universe", "Complete Universe"])

# Prevent crash if no CKPG is selected
if not selected_ckpgs:
    st.warning("⚠ Please select at least one CKPG!")
    st.stop()

# Filter dataset based on CKPG selection
df_filtered = df_summary[df_summary["CKPG"].isin(selected_ckpgs)].copy()

# Ensure the columns exist before filtering for the selected universe
required_cols = ["19SRR", "20SRR", "21SRR", "22SRR"]
if universe_toggle == "5-Year Universe":
    required_cols.append("23SRR")  # Add 2023 data if 5-year universe is selected

missing_cols = [col for col in required_cols if col not in df_filtered.columns]
if missing_cols:
    st.warning(f"⚠ The following required columns are missing: {missing_cols}")
    st.stop()

# Drop rows with missing values in required columns
df_filtered = df_filtered.dropna(subset=required_cols, how='any')

# Display CKPG Summary Metrics
st.write("### CKPG Summary Metrics")
summary_table = df_filtered.groupby("CKPG")[list(sum(metric_columns.values(), []))].mean().reset_index()
summary_table = summary_table.round(2)  # Reduce decimal places
st.dataframe(summary_table)

# Display Top Companies by Selected Metric
selected_metric = st.selectbox("Select Metric to Rank Companies", list(metric_columns.keys()))
# Ensure selected year is valid after universe change
valid_years = ["19", "20", "21", "22"]  # Default to 4-Year Universe
if universe_toggle in ["5-Year Universe", "Complete Universe"]:
    valid_years.append("23")  # Add 2023 only for 5-Year & Complete

# Auto-adjust selected year to avoid errors
selected_year = st.selectbox("Select Year", valid_years, index=len(valid_years) - 1)


# Extract short metric name without units (e.g., "SRV" instead of "Sustainable Revenue (SR) (USD Millions)")
metric_column = f"{selected_year}{metric_columns[selected_metric][0][-3:]}"

top_companies = df_filtered.sort_values(by=metric_column, ascending=False, na_position="last")[["CKPG", "Name", metric_column]].head(20)
st.write(f"### Top Companies for {selected_metric}")
st.dataframe(top_companies)

# **📊 Compute IQR (Interquartile Range)**
Q1 = df_filtered[metric_column].quantile(0.25)
Q3 = df_filtered[metric_column].quantile(0.75)
IQR = Q3 - Q1

# Compute bounds
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

# Whisker min/max
whisker_min = df_filtered[df_filtered[metric_column] >= lower_bound][metric_column].min()
whisker_max = df_filtered[df_filtered[metric_column] <= upper_bound][metric_column].max()

# Filter outliers
outliers = df_filtered[(df_filtered[metric_column] < lower_bound) | (df_filtered[metric_column] > upper_bound)]
regular_data = df_filtered[(df_filtered[metric_column] >= whisker_min) & (df_filtered[metric_column] <= whisker_max)]

# **📊 Box Plot with Outliers Highlighted**
fig = go.Figure()

# Select color scheme
ckpg_colors = pc.qualitative.Set2  # Pick a color palette

fig = go.Figure()

# Iterate over CKPGs and add a separate box for each
for i, ckpg in enumerate(df_filtered["CKPG"].unique()):
    subset = df_filtered[df_filtered["CKPG"] == ckpg]

    fig.add_trace(go.Box(
        y=subset[metric_column],
        x=[ckpg] * len(subset),  # Repeat CKPG name for alignment
        name=ckpg,
        marker_color=ckpg_colors[i % len(ckpg_colors)],  # Cycle colors
        boxpoints=False  # Hide default outlier points
    ))

# Add Outliers as Separate Points
if not outliers.empty:
    fig.add_trace(go.Scatter(
        x=outliers["CKPG"],
        y=outliers[metric_column],
        mode="markers",
        name="Outliers",
        marker=dict(color="red", size=8, symbol="circle-open"),
        text=outliers["Name"],  # Label outliers by company name
        hoverinfo="text+y"
    ))

# Format Layout
fig.update_layout(
    title=f"Distribution of {selected_metric} by CKPG",
    xaxis_title="CKPG",
    yaxis_title=selected_metric,
    showlegend=True
)

# Display Graph in Streamlit
st.plotly_chart(fig)

#st.write("✅ CKPG Data Explorer - Version 1 Complete")

#%%
