import requests
import json

# the weather.gov api uses latitude and longitude to get a location's gridX and gridY values
url = "https://api.weather.gov/points/32.7157,-117.1611"
payload={}
headers = {
# these details allow the weather service to contact you if there are some issues with your request
'User-Agent': '(some-website.com,some-email@email.com)'
}

response = requests.request("GET", url, headers=headers, data=payload)

#this is the full json response from the weather api
print(response.text)

grid_json = json.loads(response.text)

# we only want the grid details from the json
grid_x = grid_json.get("properties").get("gridX")
grid_y = grid_json.get("properties").get("gridY")
office = grid_json.get("properties").get("cwa")

url = f"https://api.weather.gov/gridpoints/{office}/{grid_x},{grid_y}/forecast/hourly"
response = requests.request("GET", url, headers=headers, data=payload)
#print(response.text)

weather_json = json.loads(response.text)

print(weather_json.get("properties").get("periods")[0].get("temperature"))
