import asyncio
import json
import os
import sys

from aiohttp import web
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


def pair_with_bluetoothctl(address: str, pin: str | None = None) -> bool:
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
                if pin is None:
                    child.sendline("")
                    child.sendline("quit")
                    child.close()
                    return False
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


async def pair_device(address: str, pin: str | None = None) -> bool:
    if sys.platform.startswith("linux"):
        return await asyncio.to_thread(pair_with_bluetoothctl, address, pin)
    try:
        async with BleakClient(address) as client:
            if not client.is_connected:
                await client.connect()
            return await client.pair()
    except Exception as e:
        print(f"❌ Pairing-Fehler: {e}")
        return False


routes = web.RouteTableDef()


@routes.get("/")
async def index(request):
    html = """
    <h1>Bluetooth Konfiguration</h1>
    <p><a href='/scan'>Geräte scannen</a></p>
    """
    return web.Response(text=html, content_type="text/html")


@routes.get("/scan")
async def scan(request):
    devices = await BleakScanner.discover(timeout=5.0)
    html = "<h1>Gefundene Geräte</h1><ul>"
    for d in devices:
        name = d.name or "Unbekannt"
        html += f"<li>{name} [{d.address}] <a href='/pair?address={d.address}'>Pair</a></li>"
    html += "</ul><p><a href='/'>Zurück</a></p>"
    return web.Response(text=html, content_type="text/html")


@routes.get("/pair")
async def pair(request):
    address = request.query.get("address")
    if not address:
        return web.Response(text="Adresse fehlt", status=400)

    pin = request.query.get("pin")
    success = await pair_device(address, pin)
    if success:
        cfg = load_config()
        cfg["device_address"] = address
        save_config(cfg)
        html = f"<p>Gerät {address} gespeichert</p><p><a href='/'>Home</a></p>"
        return web.Response(text=html, content_type="text/html")

    if pin is None:
        html = f"""
        <h1>PIN für {address}</h1>
        <form action='/pair' method='get'>
            <input type='hidden' name='address' value='{address}'>
            <label>PIN: <input name='pin'></label>
            <button type='submit'>Senden</button>
        </form>
        """
        return web.Response(text=html, content_type="text/html")

    html = f"<p>Pairing mit {address} fehlgeschlagen</p><p><a href='/'>Home</a></p>"
    return web.Response(text=html, content_type="text/html")


def main():
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, port=80)


if __name__ == "__main__":
    main()
