import json
import random
from threading import Thread, Event
from time import sleep
from typing import Optional

from flask import Flask, request

import paho.mqtt.client as mqtt

mqtt_client: Optional[mqtt.Client] = None

continue_loop = True
termination_event = Event()
mqtt_connection_event = Event()

original_secret = -1
user_set_secret = -1


def signal_handler(sig, frame):
    global continue_loop
    continue_loop = False
    termination_event.set()


def initialize_database_connection():
    # This will mock a connection to a database and do other intermediary
    # tasks. Depending on the servers "load", it may take more or less time.
    print("Starting Database connection")
    sleep(random.randint(5, 60))  # A complex initialization, as you can see...
    print("Database connection established")


def on_mqtt_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    mqtt_connection_event.set()


def connect_mqtt() -> mqtt.Client:
    client = mqtt.Client(clean_session=True, protocol=mqtt.MQTTv311)
    client.on_connect = on_mqtt_connect
    client.loop_start()
    client.connect("mqtt-broker", 1883)
    return client


def send_secret():
    # We will send the secret via MQTT to secret/number topic every second
    while continue_loop:
        mqtt_client.publish("secret/number", json.dumps({"value": original_secret}))
        termination_event.wait(1)


def main():
    global original_secret
    global mqtt_client

    initialize_database_connection()

    original_secret = random.randint(1, 100)

    mqtt_client = connect_mqtt()
    mqtt_connection_event.wait()

    app = Flask(__name__)

    @app.route("/answer", methods=["GET"])
    def answer_search():
        try:
            search_args = request.args.get("search", None, str)
            print(f"Received search args: {search_args}")
            if search_args is None:
                return "unknown", 400

            search_parts = search_args.strip().lower().split(";")
            if all(part in ["life", "universe", "everything"] for part in search_parts):
                return "42"

            return "unknown", 404
        except Exception as ex:
            return str(ex), 400

    @app.route("/secret_number", methods=["POST"])
    def set_secret():
        global user_set_secret
        try:
            req_content = request.get_json(force=True)
            if not isinstance(req_content, dict):
                raise ValueError("Request body should be a JSON object")
            if "value" not in req_content:
                raise ValueError('"value" parameter not defined in the request')
            if not isinstance(req_content["value"], int):
                raise ValueError("Provided value should be an integer")

            user_set_secret = req_content["value"]

            return "OK"
        except Exception as ex:
            return str(ex), 400

    @app.route("/secret_correct", methods=["GET"])
    def get_secret():
        if original_secret == user_set_secret:
            return "YES"
        return "NO", 409

    @app.route("/ready", methods=["GET"])
    def ready():
        return "YES"

    rest_server = Thread(
        target=app.run, args=("0.0.0.0", 80, False, False), daemon=True
    )
    rest_server.start()

    mqtt_sender = Thread(target=send_secret)
    mqtt_sender.start()

    termination_event.wait()

    mqtt_sender.join()

    try:
        mqtt_client.disconnect()
    except Exception:
        pass
    try:
        mqtt_client.loop_stop()
    except Exception:
        pass


if __name__ == "__main__":
    import signal

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    main()
