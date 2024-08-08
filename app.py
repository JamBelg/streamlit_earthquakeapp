import streamlit as st
import pandas as pd
import pydeck as pdk
import boto3
from bokeh.plotting import figure, show

# Function to read data from S3
def read_data():
    st.session_state["aws_access_key_id"] = st.secrets["aws_access_key_id"]
    st.session_state["aws_secret_access_key"] = st.secrets["aws_secret_access_key"]
    s3 = boto3.client(
        "s3",
        aws_access_key_id=st.session_state["aws_access_key_id"],
        aws_secret_access_key=st.session_state["aws_secret_access_key"],
    )
    bucket_name = "earthquakedb"
    s3_file = "data_etl.csv"
    obj = s3.get_object(Bucket=bucket_name, Key=s3_file)
    data = pd.read_csv(obj["Body"])
    data["Date UTC"] = pd.to_datetime(
        data[["Year", "UTC_Time"]].assign(SEP=" "), format="%Y %b %d"
    )
    data = data[["Date UTC", "Location", "Magnitude", "Depth", "Latitude", "Longitude"]][
        data["Magnitude"] > 0
    ]
    return data


# Streamlit app layout
st.set_page_config(
    page_title="Recorded Earthquakes in Switzerland",
    page_icon=":earth_africa:",
)

# Header
st.markdown(
    """
    <style>
    .element-container {text-align: center;}
    </style>
    """,
    unsafe_allow_html=True,
)
col1, col2, col3 = st.columns([1, 8, 1])
with col1:
    st.image("earthquake(1).png", width=60, height=60)
with col2:
    st.title("Recorded Earthquakes in Switzerland")

# Data fetching and table
data = read_data()
st.subheader("Data from Swiss Seismological Service (http://seismo.ethz.ch/en/home/)")
st.dataframe(data[["Date UTC", "Location", "Magnitude"]].head(15))

# Histogram
p = figure(
    x_range=(data["Magnitude"].min(), data["Magnitude"].max()),
    title="Earthquake's Magnitude Distribution",
)
p.hist(source=data, x="Magnitude", bins=20, fill_color="skyblue", line_color="black")
st.bokeh_chart(p, use_container_width=True)

# Map
lat = data["Latitude"].mean()
lon = data["Longitude"].mean()
tooltip = {"Date": "@{Date UTC}", "Location": "@Location", "Magnitude": "@Magnitude"}
view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=4)
layer = pdk.Layer(
    "ScatterPlotLayer",
    data=data,
    get_position=["Longitude", "Latitude"],
    get_radius=lambda x: 9 ** x["Magnitude"] + 2500,
    get_fill_color=pdk.Color("interpolate", input="Magnitude", domain=[0, data["Magnitude"].max()],
        colors=brewer.Reds[3:9]),
    get_tooltip=tooltip,
)
r = pdk.Deck(layers=[layer], initial_view_state=view_state)
st.deck(r)

# Footer
st.markdown(
    """---
    Author: Jamel Belgacem  
    This dashboard was developed with Shiny for Python.
    """,
    unsafe_allow_html=True,
)
