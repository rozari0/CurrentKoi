import time

import network
import urequests

WIFI_SSID = "WIFI_SSID"
WIFI_PASSWORD = "WIFI_PASSWORD"
API_URL = "https://currentkoi.rozario.xyz/api/v1/devices/ping"
BEARER_TOKEN = "DEVICE_KEY FROM CURRENTKOI DASHBOARD"


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        while not wlan.isconnected():
            time.sleep(1)

    print("Connected!")
    print("Network config:", wlan.ifconfig())


def send_request():
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}

    try:
        print(f"Sending POST request to {API_URL}...")
        response = urequests.post(API_URL, headers=headers)

        print("Status Code:", response.status_code)
        print("Response:", response.text)

        response.close()

    except Exception as e:
        print("Failed to send request:", e)


def main():
    connect_wifi()

    while True:
        if network.WLAN(network.STA_IF).isconnected():
            send_request()
        else:
            print("WiFi disconnected. Reconnecting...")
            connect_wifi()

        time.sleep(60)


if __name__ == "__main__":
    main()
