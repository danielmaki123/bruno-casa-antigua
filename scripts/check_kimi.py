import httpx
key = 'sk-6ZOeMqL7ty5H81nFIxbTimeloMyhYbttI3IBSXisVt6Ar0oJ'
urls = ['https://api.moonshot.cn/v1/models', 'https://api.moonshot.ai/v1/models']

for url in urls:
    try:
        response = httpx.get(url, headers={"Authorization": f"Bearer {key}"})
        print(f"{url}: {response.status_code}")
        if response.status_code == 200:
            print(f"   Modelos: {response.json()}")
        else:
            print(f"   Detalle: {response.text}")
    except Exception as e:
        print(f"{url}: Error - {e}")
