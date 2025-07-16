import asyncio
from bleak import BleakClient, BleakScanner
import config


async def pair_device(address: str) -> bool:
    try:
        async with BleakClient(address) as client:
            if not client.is_connected:
                await client.connect()
            paired = await client.pair()
            if paired:
                print(f"✅ Gepaart mit {address}")
            else:
                print(f"❌ Pairing mit {address} fehlgeschlagen")
            return paired
    except Exception as e:
        print(f"❌ Pairing-Fehler: {e}")
        return False


async def run():
    print("🔍 Suche Bluetooth-Geräte...")
    devices = await BleakScanner.discover(timeout=5.0)
    if not devices:
        print("Keine Geräte gefunden")
        return
    for idx, d in enumerate(devices, 1):
        name = d.name or "Unbekannt"
        print(f"{idx}) {name} [{d.address}]")
    choice = input("Gerät wählen (Nummer) oder Enter abbrechen: ").strip()
    if not choice.isdigit():
        print("Abgebrochen")
        return
    idx = int(choice) - 1
    if idx < 0 or idx >= len(devices):
        print("Ungültige Auswahl")
        return
    address = devices[idx].address
    print(f"🔗 Versuche Pairing mit {address} ...")
    if await pair_device(address):
        cfg = config.load_config()
        cfg["device_address"] = address
        config.save_config(cfg)
        print(f"Gerät {address} gespeichert")


if __name__ == "__main__":
    asyncio.run(run())
