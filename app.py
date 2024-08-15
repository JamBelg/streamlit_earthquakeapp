import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import numpy as np
import pydeck as pdk
import boto3
import requests
from io import StringIO
from bokeh.plotting import figure, show


@st.cache_data
def read_data():
    data = pd.read_csv('C:/users/ch1jbelgac1/Work Folders/MyDocuments/GitHub/streamlit_earthquakeapp/data_offline.csv')
    data.rename(columns={'Latitude': 'latitude', 'Longitude': 'longitude'}, inplace=True)

    data = data[['Date UTC','Location','Magnitude','latitude','longitude']]
    return data

@st.cache_data
def load_csv_from_github(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        csv_data = response.content.decode('utf-8')
        df = pd.read_csv(pd.compat.StringIO(csv_data))
        return df
    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        st.error(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        st.error(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        st.error(f"An error occurred: {req_err}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
    return None


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
st.title("Recorded Earthquakes in Switzerland")

# Data fetching and table
data_load_state = st.text('Loading data...')
data = load_csv_from_github('https://raw.githubusercontent.com/JamBelg/streamlit_earthquakeapp/main/filename.csv')
if data is not None:
    data_load_state.text("Done!")
else:
    st.warning("Failed to load the CSV file.")

min_mag, max_mag = st.slider(label='Select Magnitude Range',
                             min_value=0.0,
                             max_value=8.0,
                             value=(3.0, 5.0),
                             step=0.5)
filtered_data = data[(data['Magnitude']>=min_mag) & (data['Magnitude']<=max_mag)]

if st.checkbox('Show raw data'):
    st.subheader('Raw data')
    st.write(filtered_data.head(20))
    st.markdown("h5(red[Data from Swiss Seismological Service (http://seismo.ethz.ch/en/home/)])")

st.subheader('Magnitude distribution')
# Calculate histogram values
hist_values, bin_edges = np.histogram(filtered_data['Magnitude'], bins=10, range=(min_mag, max_mag))

# Create a DataFrame for the histogram values and corresponding labels
hist_df = pd.DataFrame({
    'Magnitude Range': bin_edges[:-1].round(2).astype(str),  # Create labels for bins
    'Count': hist_values
})

# Display the bar chart using st.bar_chart
st.bar_chart(hist_df.set_index('Magnitude Range'))

st.subheader('Map')
# Define the bounds (min and max latitude and longitude)
bounds = [
    [filtered_data['latitude'].min(), filtered_data['longitude'].min()],
    [filtered_data['latitude'].max(), filtered_data['longitude'].max()]
]

# Create a map centered on the average location with bounds
m = folium.Map(location=[filtered_data['latitude'].mean(),
                         filtered_data['longitude'].mean()],
               zoom_start=5)

# Fit the map to the bounds
m.fit_bounds(bounds)

# Function to scale the radius
#def scale_radius(magnitude):
#    return 2 ** magnitude  # Exponential scaling
def scale_radius(magnitude):
    return np.log1p(magnitude) * 10  # Logarithmic scaling, multiplied to enhance size

# Add points to the map
for i, row in filtered_data.iterrows():
    folium.CircleMarker(
        location=[row['latitude'], row['longitude']],
        radius=scale_radius(row['Magnitude']),  # Apply the scaling function
        color='red',
        fill=True,
        fill_color='red',
        popup=f"Magnitude: {row['Magnitude']}"
    ).add_to(m)

#col1, col2 = st.columns([8, 5])


# Display the map in Streamlit
#with col1:
st_folium(m, width=725)

st.subheader('Frequence of recorded earthquakes')
# Count the occurrences for each date
date_counts = filtered_data['Date UTC'].value_counts().sort_index()

# Create a DataFrame from the counts
date_counts_df = pd.DataFrame({'Date': date_counts.index, 'Count': date_counts.values})

# Plot the counts using st.bar_chart
#with col2:
st.bar_chart(date_counts_df.set_index('Date'))


# Footer
st.markdown(
    """---
    Author: Jamel Belgacem  
    This dashboard was developed with Streamlite.
    """,
    unsafe_allow_html=True,
)
