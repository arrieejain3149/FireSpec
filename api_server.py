from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import joblib
import io
import os
from src.model import FireImpactModel
from src.selector import select_response_portfolio

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "IGNIS FastAPI Backend Server Running", "status": "ok", "docs": "/docs"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def map_to_latlon(x, y):
    # Coastal Bay Coordinates (Setubal, Portugal)
    min_lon, max_lon = -9.00, -8.70
    min_lat, max_lat = 38.40, 38.60
    lon = min_lon + ((x - 1) / 8.0) * (max_lon - min_lon)
    lat = min_lat + ((9 - y) / 8.0) * (max_lat - min_lat)
    return lat, lon

@app.post("/predict")
async def predict_portfolio(file: UploadFile = File(...)):
    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents))
    
    # --- NEW: Fire Classification & Industry Bifurcation ---
    def classify_fire(row):
        if row.get('ISI', 0) > 12.0 and row.get('wind', 0) > 5.0:
            return "Crown Fire (High Velocity)"
        elif row.get('DC', 0) > 400.0:
            return "Ground Fire (Smoldering)"
        else:
            return "Surface Fire (Brush)"
            
    def get_industry_sector(x, y):
        val = (x * 3 + y * 7) % 4
        if val == 0: return "Commercial Forestry"
        elif val == 1: return "Agriculture"
        elif val == 2: return "Residential (WUI)"
        else: return "Infrastructure"

    df['fire_type'] = df.apply(classify_fire, axis=1)
    df['industry_sector'] = df.apply(lambda r: get_industry_sector(r.get('X', 0), r.get('Y', 0)), axis=1)
    # -------------------------------------------------------
    
    pipeline = joblib.load('artifacts/pipeline.pkl')
    model = FireImpactModel()
    model.load('artifacts/model.pkl')
    
    X = df.copy()
    # Drop the new synthetic columns before passing to the strict ML pipeline
    X = X.drop(['fire_type', 'industry_sector'], axis=1, errors='ignore')
    
    has_target = 'area' in X.columns
    if has_target:
        X = X.drop('area', axis=1)
        
    X_processed = pipeline.transform(X)
    preds = model.predict(X_processed)
    
    X_for_selection = X.copy()
    X_for_selection['original_index'] = X.index
    selected_indices = select_response_portfolio(X_for_selection, preds, top_n=25, max_per_cell=4)
    
    portfolio = df.iloc[selected_indices].copy()
    portfolio['ranking_score'] = preds[selected_indices]
    
    lats, lons = zip(*portfolio.apply(lambda row: map_to_latlon(row['X'], row['Y']), axis=1))
    portfolio['lat'] = lats
    portfolio['lon'] = lons
    
    # Slight jitter for overlap
    portfolio['lon'] += np.random.uniform(-0.008, 0.008, size=len(portfolio))
    portfolio['lat'] += np.random.uniform(-0.008, 0.008, size=len(portfolio))
    
    cell_counts = portfolio.groupby(['X', 'Y']).size().reset_index(name='count')
    portfolio = portfolio.merge(cell_counts, on=['X', 'Y'])
    
    importance = model.model.feature_importances_
    features = pipeline.num_features
    feat_imp = [{"name": f, "value": float(i)} for f, i in zip(features, importance)]
    feat_imp.sort(key=lambda x: x["value"], reverse=True)
    
    outliers = []
    regression_data = []
    
    if has_target:
        sample = df.head(100)
        outliers = [{"raw": float(a), "log": float(np.log1p(a))} for a in sample['area']]
        
        y_true = np.log1p(df['area'].values)
        m, b = np.polyfit(y_true, preds, 1)
        
        # Calculate trendline points
        min_x = float(np.min(y_true))
        max_x = float(np.max(y_true))
        
        for t, p in zip(y_true[:100], preds[:100]):
            regression_data.append({"x": float(t), "y": float(p)})
            
        eq = f"Pred = {m:.2f} * True + {b:.2f}"
        reg_x, reg_y = "True Log(Area)", "Predicted Impact"
    else:
        temp = df['temp'].values
        m, b = np.polyfit(temp, preds, 1)
        
        min_x = float(np.min(temp))
        max_x = float(np.max(temp))
        
        for t, p in zip(temp[:100], preds[:100]):
            regression_data.append({"x": float(t), "y": float(p)})
            
        eq = f"Pred = {m:.2f} * Temp + {b:.2f}"
        reg_x, reg_y = "Temperature (C)", "Predicted Impact"

    # Add trendline endpoints for recharts line
    trendline = [
        {"x": min_x, "line": float(m * min_x + b)},
        {"x": max_x, "line": float(m * max_x + b)}
    ]

    return {
        "portfolio": portfolio.to_dict(orient="records"),
        "feature_importance": feat_imp,
        "outlier_data": outliers,
        "regression": {
            "data": regression_data,
            "trendline": trendline,
            "equation": eq,
            "xLabel": reg_x,
            "yLabel": reg_y
        },
        "raw_table": df.head(30).to_dict(orient="records")
    }

@app.get("/nasa-firms")
async def trigger_nasa_firms():
    """
    Simulates fetching near real-time NASA FIRMS VIIRS data.
    Generates synthetic telemetry based on high Fire Radiative Power (FRP) and runs it through the ML engine.
    """
    n_rows = 500
    lat_center, lon_center = 38.5, -8.85
    
    lats = np.random.normal(lat_center, 0.5, n_rows)
    lons = np.random.normal(lon_center, 0.5, n_rows)
    frps = np.random.exponential(50.0, n_rows) + 15.0 # Fire Radiative Power
    
    X_grid = np.clip(((lons - (lon_center - 0.5)) / 1.0 * 10).astype(int), 1, 9)
    Y_grid = np.clip(((lats - (lat_center - 0.5)) / 1.0 * 10).astype(int), 1, 9)
    
    # Synthesize extreme weather based on FRP
    temp = 30.0 + (frps / 20.0) + np.random.normal(0, 2, n_rows)
    wind = 15.0 + (frps / 30.0) + np.random.normal(0, 2, n_rows)
    ffmc = 90.0 + (frps / 50.0) + np.random.normal(0, 1, n_rows)
    
    df = pd.DataFrame({
        'X': X_grid, 'Y': Y_grid,
        'month': np.random.choice(['aug', 'sep'], n_rows),
        'day': np.random.choice(['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'], n_rows),
        'FFMC': np.clip(ffmc, 85, 99.9),
        'DMC': np.clip(frps * 1.5, 50, 300),
        'DC': np.clip(frps * 3.0, 200, 800),
        'ISI': np.clip(wind * 0.7, 5, 30),
        'temp': np.clip(temp, 20, 45),
        'RH': np.clip(30 - (frps/10), 10, 50),
        'wind': np.clip(wind, 10, 30),
        'rain': 0.0,
        'nasa_frp': frps,
        'nasa_confidence': np.where(frps > 40, 'High', 'Nominal'),
        'satellite': 'VIIRS S-NPP'
    })
    
    def classify_fire(row):
        if row.get('ISI', 0) > 12.0 and row.get('wind', 0) > 5.0: return "Crown Fire (High Velocity)"
        elif row.get('DC', 0) > 400.0: return "Ground Fire (Smoldering)"
        else: return "Surface Fire (Brush)"
            
    def get_industry_sector(x, y):
        val = (x * 3 + y * 7) % 4
        if val == 0: return "Commercial Forestry"
        elif val == 1: return "Agriculture"
        elif val == 2: return "Residential (WUI)"
        else: return "Infrastructure"

    df['fire_type'] = df.apply(classify_fire, axis=1)
    df['industry_sector'] = df.apply(lambda r: get_industry_sector(r.get('X', 0), r.get('Y', 0)), axis=1)
    
    pipeline = joblib.load('artifacts/pipeline.pkl')
    model = FireImpactModel()
    model.load('artifacts/model.pkl')
    
    X_ml = df.drop(['fire_type', 'industry_sector', 'nasa_frp', 'nasa_confidence', 'satellite'], axis=1, errors='ignore')
    X_processed = pipeline.transform(X_ml)
    preds = model.predict(X_processed)
    
    X_for_selection = X_ml.copy()
    X_for_selection['original_index'] = X_ml.index
    selected_indices = select_response_portfolio(X_for_selection, preds, top_n=25, max_per_cell=4)
    
    portfolio = df.iloc[selected_indices].copy()
    portfolio['ranking_score'] = preds[selected_indices]
    
    # Overwrite the standard grid mapping with the precise simulated NASA coordinates
    portfolio['lat'] = lats[selected_indices]
    portfolio['lon'] = lons[selected_indices]
    
    # Generate same payload
    cell_counts = portfolio.groupby(['X', 'Y']).size().reset_index(name='count')
    portfolio = portfolio.merge(cell_counts, on=['X', 'Y'])
    
    importance = model.model.feature_importances_
    features = pipeline.num_features
    feat_imp = [{"name": f, "value": float(i)} for f, i in zip(features, importance)]
    feat_imp.sort(key=lambda x: x["value"], reverse=True)
    
    temp_vals = df['temp'].values
    m, b = np.polyfit(temp_vals, preds, 1)
    min_x, max_x = float(np.min(temp_vals)), float(np.max(temp_vals))
    
    regression_data = [{"x": float(t), "y": float(p)} for t, p in zip(temp_vals[:100], preds[:100])]
    trendline = [{"x": min_x, "line": float(m * min_x + b)}, {"x": max_x, "line": float(m * max_x + b)}]
    
    return {
        "portfolio": portfolio.to_dict(orient="records"),
        "feature_importance": feat_imp,
        "outlier_data": [],
        "regression": {
            "data": regression_data,
            "trendline": trendline,
            "equation": f"Pred = {m:.2f} * Temp + {b:.2f}",
            "xLabel": "Temperature (C)",
            "yLabel": "Predicted Impact"
        },
        "raw_table": df.head(30).to_dict(orient="records")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
