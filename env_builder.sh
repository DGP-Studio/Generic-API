#!/bin/bash

# This script is used to append Homa-Server's internal IP address to the .env file

CONTAINER_NAME="Homa-Server"
CONTAINER_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$CONTAINER_NAME")

if [ -z "$CONTAINER_IP" ]; then
  echo "Error: Failed to retrieve IP address for container $CONTAINER_NAME"
  exit 1
fi

echo "HOMA_SERVER_IP=$CONTAINER_IP" > ".env"

echo "Updated $ENV_FILE with HOMA_SERVER_IP=$CONTAINER_IP"
