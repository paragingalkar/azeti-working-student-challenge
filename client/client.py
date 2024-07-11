from threading import Event
from typing import Optional, Any
import json, time
import requests

import paho.mqtt.client as mqtt


# Feel free to add more libraries (e.g.: The REST Client library)

mqtt_client: Optional[mqtt.Client] = None

mqtt_connection_event = Event()

secret = -1
base_url = "http://server:80"


def send_secret_rest(secret_value: int):
    global secret
    global base_url
    # Add the logic to send this secret value to the REST server.
    # We want to send a JSON structure to the endpoint `/secret_number`, using
    # a POST method.
    #
    # Assuming secret_value = 50, then the request will contain the following
    # body: {"value": 50}
    body = {"value": secret_value}
    try:
        response = requests.post(f"{base_url}/secret_number", json=body)
        if response.status_code == 200:
            print("Secret number sent to the server")
            secret = 1
        else:
            print(f"Failed to send secret number to the server: {response.status_code}")
    except requests.exceptions.RequestException as ex:
        print(f"Error sending secret to the server: {ex}")


def check_secret_correct():
    global base_url

    try:
        response = requests.get(f"{base_url}/secret_correct")
        if response.status_code == 200:
            print("Secret correctly set on the server")
        else:
            print("Secret mismatched")
    except requests.exceptions.RequestException as e:
        print(f"Error checking secret correctness: {e}")


def on_mqtt_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    mqtt_connection_event.set()


def on_mqtt_message(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage):
    # Implement the logic to parse the received secret (we receive a json, but
    # we are interested just on the value) and send this value to the REST
    # server... or maybe the sending to REST should be done somewhere else...
    # do you have any idea why?
    try:
        if msg is not None:
            secret_value = json.loads(msg.payload.decode())["value"]
            send_secret_rest(secret_value)
    except json.JSONDecodeError:
        print("Cannot decode JSON message")


def connect_mqtt() -> mqtt.Client:
    client = mqtt.Client(clean_session=True, protocol=mqtt.MQTTv311)
    client.on_connect = on_mqtt_connect
    client.on_message = on_mqtt_message
    client.connect("mqtt-broker", 1883)
    client.loop_start()
    return client


def wait_for_server_ready():
    global base_url
    # Implement code to wait until the server is ready, it's up to you how
    # to do that. Our advice: Check the server source code and check if there
    # is anything useful that can help.
    # Hint: If you prefer, feel free to delete this method, use an external
    # tool and incorporate it in the Dockerfile
    timeout = 120
    print("Waiting for server")
    for i in range(timeout):
        try:
            response = requests.get(f"{base_url}/ready")
            if response.status_code == 200:
                print("Server is ready.")
                return
        except requests.ConnectionError:
            pass
        print("Waiting for the server to be ready...")
        i += 5
        time.sleep(5)

    raise TimeoutError("Server did not become ready within the specified timeout.")


def main():
    global mqtt_client, secret, base_url

    wait_for_server_ready()

    mqtt_client = connect_mqtt()
    mqtt_connection_event.wait()

    # At this point, we have our MQTT connection established, now we need to:
    # 1. Subscribe to the MQTT topic: secret/number
    # 2. Parse the received message and extract the secret number
    # 3. Send this number via REST to the server, using a POST method on the
    # resource `/secret_number`, with a JSON body like: {"value": 50}
    # 4. (Extra) Check the REST resource `/secret_correct` to ensure it was
    # properly set
    # 5. Terminate the script, only after at least a value was sent

    mqtt_client.subscribe("secret/number")
    while secret == -1:
        time.sleep(1)

    if secret == 1:
        check_secret_correct()

    try:
        mqtt_client.disconnect()
    except Exception:
        pass
    try:
        mqtt_client.loop_stop()
    except Exception:
        pass


if __name__ == "__main__":
    main()
