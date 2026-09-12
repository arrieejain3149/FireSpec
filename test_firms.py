import requests
import pandas as pd
import io

url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Europe_24h.csv"
try:
    res = requests.get(url, timeout=10)
    print(res.status_code)
    df = pd.read_csv(io.StringIO(res.text))
    print(df.head())
except Exception as e:
    print(e)
