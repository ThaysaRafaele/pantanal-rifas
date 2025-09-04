import os
import requests

access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
url = "https://api.mercadolibre.com/users/me"

headers = {"Authorization": f"Bearer {access_token}"}

response = requests.get(url, headers=headers)
print(response.json())
