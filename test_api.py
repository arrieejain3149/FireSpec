import requests
import json

with open('forestfires.csv', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/predict', files=files)

print("Status Code:", response.status_code)
if response.status_code != 200:
    print("Error Details:", response.text)
else:
    print("Success! Keys:", response.json().keys())
