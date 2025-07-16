# Dockerized Blood Pressure Fetcher

This project interacts with a Bluetooth-enabled blood pressure monitor. It presents a simple
console menu with three options:

1. **Configuration** – search and pair with a Bluetooth device
2. **Start/Stop Fetching** – begin or stop receiving measurements
3. **Exit** – quit the program

The menu is displayed when running the container and can be operated via the terminal.

## Build

```bash
docker build -t bp-fetcher .
```

## Run

Run with an interactive terminal to use the menu:

```bash
docker run -it --rm bp-fetcher
```

Additional flags may be required to access Bluetooth hardware depending on your system
(e.g. `--net=host --privileged`).
