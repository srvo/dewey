import requests

url = "https://api.attio.com/v2/objects/people/records/query"

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": "Bearer db05495d98ca3364876e4070fd3acf4510f4d0c5b85f0b353944e4cf94385544"
}

response = requests.post(url, headers=headers)

print(response.text)
