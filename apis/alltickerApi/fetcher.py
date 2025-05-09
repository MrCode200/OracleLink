import requests

url = "https://quote.alltick.io/quote-stock-b-api/kline"
params = {
    "token": "cd3ec6e46be2d11831ae3b10264c419c-c-app",
    "query": '{"trace": "python_http_test1", "data": {"code": "EURUSD", "kline_type": 1, "query_kline_num": 10}}'
}

response = requests.get(url, params=params)
data = response.json()
print(data)
