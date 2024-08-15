import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import boto3
#from bokeh.plotting import figure, show
import folium
from streamlit_folium import st_folium

# Function to read data from S3
@st.cache_data
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

    data['datetime_str'] = data['Year'].astype(str) + ' ' + data['UTC_Time']
    data['Date UTC'] = pd.to_datetime(data['datetime_str'], format='%Y %b %d %H:%M:%S')
    data.rename(columns={'Latitude': 'latitude', 'Longitude': 'longitude'}, inplace=True)
    data = data[(data["Magnitude"] > 0) & 
                (data['Date UTC'] >= '2018-01-01')][["Date UTC", "Location", "Magnitude", "Depth", "latitude", "longitude"]]
    return data




# Streamlit app layout
st.set_page_config(
    page_title="Earthquakes in Switzerland",
    page_icon=":earth_africa:",
)

st.sidebar.title("About")


st.sidebar.markdown(
    """
    This application provides detailed analysis and visualization of recorded earthquakes in Switzerland.
    Discover insights into seismic activity and track historical earthquake data with interactive charts and maps.
    
    Data are from [Swiss Seismological Service](http://seismo.ethz.ch/en/home/).
    
    **Developped by Jamel Belgacem**
    
    Connect with me:

    <a href="https://www.linkedin.com/in/jamel-belgacem-289606a7/" target="_blank">
        <img src="https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png" width="30" height="30" alt="LinkedIn"/>
    </a>
    
    <a href="https://github.com/JamBelg" target="_blank">
        <img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Octicons-mark-github.svg" width="30" height="30" alt="GitHub"/>
    </a>
    """,
    unsafe_allow_html=True
)


# CSS
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
    st.image("earthquake(1).png", width=60)
with col2:
    st.title("Earthquakes in Switzerland")

# Data fetching and table
data_load_state = st.text('Loading data...')
data = read_data()
data_load_state.text("Done!")

st.subheader("Filter data:")
min_mag, max_mag = st.slider(label='Select Magnitude Range',
                             min_value=0.0,
                             max_value=8.0,
                             value=(1.0, 5.0),
                             step=0.5)
filtered_data = data[(data['Magnitude']>=min_mag) & (data['Magnitude']<=max_mag)]

if st.checkbox('Show raw data'):
    st.subheader('Raw data')
    st.write(filtered_data.head(20))

st.subheader("Earthquake's magnitude distribution")
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
def scale_radius(magnitude):
    return 2 ** (magnitude)  # Exponential scaling
#def scale_radius(magnitude):
#    return np.log1p(magnitude) * 20  # Logarithmic scaling, multiplied to enhance size

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


# Display the map in Streamlit
st_folium(m, width=725)

st.subheader('Frequence of recorded earthquakes')
# Group by year and month and count the occurrences
filtered_data['Year-Month'] = filtered_data['Date UTC'].dt.to_period('M')
month_counts = filtered_data['Year-Month'].value_counts().sort_index()

# Convert the result to a DataFrame
month_counts_df = pd.DataFrame({'Month': month_counts.index.astype(str), 'Count': month_counts.values})

# Plot the counts using st.bar_chart
st.bar_chart(month_counts_df.set_index('Month'))
