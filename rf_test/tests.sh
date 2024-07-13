#!/usr/bin/env sh

# Hint: Add something here to wait until the server is ready
server_url="http://server:80/ready"
echo "Waiting for the server to start..."

while ! wget -q --spider "$server_url"
do
    echo "server not ready"
    sleep 5
done

echo "Server started"

mkdir -p results
robot -d results test-server.robot
