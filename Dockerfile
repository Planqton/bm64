FROM python:3.11-slim

# Benötigte Pakete für Bluetooth
RUN apt-get update && \
    apt-get install -y bluetooth bluez libbluetooth-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir bleak openpyxl pexpect aiohttp

# Verzeichnis für persistente Daten
VOLUME ["/appdata"]
ENV DATA_DIR=/appdata

CMD ["python", "main.py"]
