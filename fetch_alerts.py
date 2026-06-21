import requests
import time

# Give API time to process some stream data
time.sleep(2)

try:
    res = requests.get("http://localhost:8000/api/v1/alerts?limit=5")
    print(res.json())
except Exception as e:
    print(e)
