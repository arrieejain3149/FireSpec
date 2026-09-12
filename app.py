import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import base64
import joblib
import os
from src.model import FireImpactModel
from src.selector import select_response_portfolio

st.set_page_config(page_title="Firespec - Wildfire Response", layout="wide", initial_sidebar_state="collapsed")

# --- Custom CSS for Awwwards Aesthetic ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400..900;1,400..900&family=Inter:wght@300;400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #050505;
}

h1, h2, h3, h4 {
    font-family: 'Playfair Display', serif !important;
    font-weight: 600;
    letter-spacing: 0.5px;
}

/* Hide default streamlit headers/footers */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}

/* Button Styling */
div.stButton > button {
    background: transparent !important;
    border: 1px solid #00E5FF !important;
    color: #00E5FF !important;
    border-radius: 0 !important;
    padding: 0.75rem 2rem !important;
    font-family: 'Inter', sans-serif !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    transition: all 0.3s ease !important;
}

div.stButton > button:hover {
    background: #00E5FF !important;
    color: #000000 !important;
    box-shadow: 0 0 20px rgba(0, 229, 255, 0.4) !important;
}

/* Animations */
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
.animate-in {
    animation: fadeInUp 1s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.logo-container {
    text-align: center;
    margin-bottom: 3rem;
    margin-top: 1rem;
}
.logo-container img {
    filter: invert(1);
    max-width: 350px;
}
</style>
""", unsafe_allow_html=True)

# --- Logo Rendering ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

if os.path.exists('logo.png'):
    logo_base64 = get_base64_of_bin_file('logo.png')
    st.markdown(
        f'<div class="animate-in logo-container"><img src="data:image/png;base64,{logo_base64}"></div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown("<h1 style='text-align: center;'>Firespec</h1>", unsafe_allow_html=True)

# --- Intro ---
st.markdown("<div class='animate-in' style='text-align: center; margin-bottom: 4rem;'><h3 style='color: #666; font-family: \"Inter\", sans-serif !important; font-weight: 300;'>AI-Driven Constrained Wildfire Response Prioritization</h3></div>", unsafe_allow_html=True)

# Ensure models are trained
if not os.path.exists('artifacts/pipeline.pkl') or not os.path.exists('artifacts/model.pkl'):
    st.error("Model artifacts not found. Please train the model first by running `python train.py` in the terminal.")
    st.stop()

uploaded_file = st.file_uploader("UPLOAD SATELLITE TELEMETRY (CSV)", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # Center the button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        start_btn = st.button("Authorize AI Deployment")
    
    if start_btn:
        with st.spinner("Analyzing atmospheric telemetry & calculating deployment vectors..."):
            pipeline = joblib.load('artifacts/pipeline.pkl')
            model = FireImpactModel()
            model.load('artifacts/model.pkl')
            
            X = df.copy()
            if 'area' in X.columns:
                X = X.drop('area', axis=1)
                
            X_processed = pipeline.transform(X)
            preds = model.predict(X_processed)
            
            X_for_selection = X.copy()
            X_for_selection['original_index'] = X.index
            selected_indices = select_response_portfolio(X_for_selection, preds, top_n=25, max_per_cell=4)
            
            portfolio = df.iloc[selected_indices].copy()
            portfolio['ranking_score'] = preds[selected_indices]
            portfolio = portfolio.sort_values(by='ranking_score', ascending=False).reset_index(drop=True)
            
            st.markdown("<br><hr style='border-color: #222;'><br>", unsafe_allow_html=True)
            st.success("Deployment Authorized. 25 Teams Dispatched.")
            
            # --- 3D MAP LOGIC ---
            # Map X(1-9), Y(1-9) to Lat/Lon for Montesinho Park
            def map_to_latlon(x, y):
                min_lon, max_lon = -6.90, -6.50
                min_lat, max_lat = 41.80, 42.00
                lon = min_lon + ((x - 1) / 8.0) * (max_lon - min_lon)
                lat = min_lat + ((9 - y) / 8.0) * (max_lat - min_lat)
                return lat, lon
                
            portfolio['lat'], portfolio['lon'] = zip(*portfolio.apply(lambda row: map_to_latlon(row['X'], row['Y']), axis=1))
            
            # 1. Satellite Base Map Layer (Free Esri Tiles)
            satellite_layer = pdk.Layer(
                "TileLayer",
                data="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                min_zoom=0,
                max_zoom=19,
                opacity=0.6,
            )
            
            # 2. Uber H3 Style Hexagon Layer
            # HexagonLayer automatically groups points at the same location.
            # Color range assigns color based on the number of points in the hex!
            hex_layer = pdk.Layer(
                "HexagonLayer",
                data=portfolio,
                get_position='[lon, lat]',
                radius=1800, # Hexagon radius in meters
                elevation_scale=5000,
                extruded=True,
                # 4 Colors mapping to 1, 2, 3, and 4 teams in the same Hex cell
                color_range=[
                    [0, 229, 255, 120],  # 1 deployment
                    [0, 229, 255, 180],  # 2 deployments
                    [0, 229, 255, 255],  # 3 deployments
                    [255, 87, 34, 255]   # 4 deployments (Neon Orange - Capacity Reached)
                ],
                pickable=True,
                auto_highlight=True,
            )
            
            # Start zoomed into Portugal with a nice 3D pitch
            view_state = pdk.ViewState(
                longitude=-6.7,
                latitude=41.9,
                zoom=8.5,
                pitch=55,
                bearing=-15
            )
            
            r = pdk.Deck(
                layers=[satellite_layer, hex_layer],
                initial_view_state=view_state,
                map_provider=None, # Disables Mapbox to allow our Satellite TileLayer to render
                tooltip={"html": "<div style='font-family: Inter;'><b>Hexagon Cell</b><br/>Elevation = Predicted Severity<br/>Color = Team Density (Max 4)</div>"}
            )
            
            st.markdown("<h2 style='text-align: center; margin-bottom: 2rem;'>Global Telemetry Map</h2>", unsafe_allow_html=True)
            st.pydeck_chart(r)
            
            st.markdown("<div style='text-align: center; color: #888; margin-top: -1rem; margin-bottom: 4rem; font-family: Inter; letter-spacing: 1px;'>Interactive 3D Hexagons: Cyan = Stable Deployment (1-3) | <span style='color: #FF5722;'>Orange = Cell Capacity Reached (4)</span></div>", unsafe_allow_html=True)
            
            # --- TABLE ---
            st.markdown("<h2>Deployment Manifest</h2>", unsafe_allow_html=True)
            st.dataframe(portfolio.drop(['lat', 'lon', 'color', 'count'], axis=1, errors='ignore'), use_container_width=True)
            
            csv = portfolio.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="DOWNLOAD SECURE MANIFEST (CSV)",
                data=csv,
                file_name='firespec_portfolio.csv',
                mime='text/csv',
            )
