import pandas as pd
import numpy as np

n_rows = 50000

print(f"Generating {n_rows} rows of dummy telemetry data...")

# Generate realistic ranges based on the Montesinho dataset
# Enforcing the EXACT column order expected by the pipeline:
# X,Y,month,day,FFMC,DMC,DC,ISI,temp,RH,wind,rain
df = pd.DataFrame({
    'X': np.random.randint(1, 10, n_rows),
    'Y': np.random.randint(2, 10, n_rows),
    'month': np.random.choice(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], n_rows),
    'day': np.random.choice(['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'], n_rows),
    'FFMC': np.round(np.random.uniform(18.7, 96.2, n_rows), 1),
    'DMC': np.round(np.random.uniform(1.1, 291.3, n_rows), 1),
    'DC': np.round(np.random.uniform(7.9, 860.6, n_rows), 1),
    'ISI': np.round(np.random.uniform(0.0, 56.1, n_rows), 1),
    'temp': np.round(np.random.uniform(5.0, 42.0, n_rows), 1),
    'RH': np.round(np.random.uniform(15.0, 100.0, n_rows), 1),
    'wind': np.round(np.random.uniform(0.0, 15.0, n_rows), 1),
    'rain': np.round(np.random.exponential(0.1, n_rows).clip(0, 6.4), 1)
})

# Add some synthetic 'high risk' anomalies
anomaly_idx = np.random.choice(n_rows, size=int(n_rows * 0.05), replace=False)
df.loc[anomaly_idx, 'temp'] = np.random.uniform(35.0, 45.0, len(anomaly_idx))
df.loc[anomaly_idx, 'wind'] = np.random.uniform(10.0, 20.0, len(anomaly_idx))
df.loc[anomaly_idx, 'RH'] = np.random.uniform(10.0, 25.0, len(anomaly_idx))
df.loc[anomaly_idx, 'FFMC'] = np.random.uniform(90.0, 99.0, len(anomaly_idx))

df.to_csv('data/high_volume_test.csv', index=False)
print("Saved to data/high_volume_test.csv")
