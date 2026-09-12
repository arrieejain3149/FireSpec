import streamlit as st
import pydeck as pdk

sat_layer = pdk.Layer(
    'TileLayer',
    data='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
)

r = pdk.Deck(layers=[sat_layer], map_style=None, initial_view_state=pdk.ViewState(longitude=-6.7, latitude=41.9, zoom=5))
st.pydeck_chart(r)
