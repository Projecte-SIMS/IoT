Raspberry Agent

Usage:
 - Set environment variables DEVICE_ID (required) and SERVER_WS (e.g. ws://your.server:8000).
 - Optionally set RELAY0_PIN to the GPIO pin used by the relay (default 17).
 - Install requirements: pip install -r requirements.txt
 - Run locally: python agent.py
 - Or build Docker image: docker build -t raspi-agent . and run with env vars:
    docker run --rm -e DEVICE_ID=device123 -e SERVER_WS=ws://your.server:8000 raspi-agent

Notes:
 - On a real Raspberry, gpiozero will control the GPIO; on other platforms a MockRelay is used.
 - The agent keeps a persistent WebSocket to the server and sends periodic status updates and acknowledgements.
