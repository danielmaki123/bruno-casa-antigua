import httpx
key = 'sk-F1DQzaqkdYNbUwGwcGz1XUPEJPXIn3NQn7bPabG8gMrKo5Mz'
url = 'https://api.moonshot.ai/v1/models'

try:
    response = httpx.get(url, headers={"Authorization": f"Bearer {key}"})
    print(f"{url}: {response.status_code}")
    if response.status_code == 200:
        models = response.json().get('data', [])
        for m in models:
            print(f" - {m['id']}")
    else:
        print(f"   Detalle: {response.text}")
except Exception as e:
    print(f"{url}: Error - {e}")
