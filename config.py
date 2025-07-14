import asyncio
import json
import os
import sys

from bleak import BleakClient, BleakScanner

DATA_DIR = os.getenv("DATA_DIR", "/appdata")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(cfg):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f)


def pair_with_bluetoothctl(address: str) -> bool:
    """Pairing via ``bluetoothctl`` unter Linux mit PIN-/Passkey-Abfrage."""
    try:
        import pexpect
    except ImportError:
        print("pexpect nicht installiert")
        return False

    child = pexpect.spawn("bluetoothctl", encoding="utf-8")
    try:
        child.expect("#", timeout=5)
        child.sendline("agent KeyboardOnly")
        child.sendline("default-agent")
        child.sendline(f"pair {address}")
        while True:
            idx = child.expect([
                "Enter PIN code:",
                r"Confirm passkey .*\[y/N\]",
                "Pairing successful", "Failed to pair",
                pexpect.EOF, pexpect.TIMEOUT
            ], timeout=30)
            if idx == 0:
                pin = input("PIN: ")
                child.sendline(pin)
            elif idx == 1:
                child.sendline("yes")
            elif idx == 2:
                child.sendline("quit")
                child.close()
                return True
            else:
                child.sendline("quit")
                child.close()
                return False
    except Exception as e:
        print(f"bluetoothctl-Fehler: {e}")
        return False


async def pair_device(address: str) -> bool:
    if sys.platform.startswith("linux"):
        return await asyncio.to_thread(pair_with_bluetoothctl, address)
    try:
        async with BleakClient(address) as client:
            if not client.is_connected:
                await client.connect()
            return await client.pair()
    except Exception as e:
        print(f"❌ Pairing-Fehler: {e}")
        return False


async def configure():
    print("\n🔍 Suche Bluetooth-Geräte...")
    devices = await BleakScanner.discover(timeout=5.0)
    if not devices:
        print("Keine Geräte gefunden")
        return
    for idx, d in enumerate(devices, 1):
        name = d.name or "Unbekannt"
        print(f"{idx}) {name} [{d.address}]")
    try:
        choice = input("Gerät wählen (Nummer) oder Enter abbrechen: ").strip()
    except EOFError:
        print()
        return
    if choice.isdigit():
        i = int(choice) - 1
        if 0 <= i < len(devices):
            address = devices[i].address
            print(f"🔗 Versuche Pairing mit {address} ...")
            if await pair_device(address):
                cfg = load_config()
                cfg["device_address"] = address
                save_config(cfg)
                print(f"Gerät {address} gespeichert")
        else:
            print("Ungültige Auswahl")


if __name__ == "__main__":
    asyncio.run(configure())
