import asyncio
from bleak import BleakClient, BleakScanner
from datetime import datetime
import os
from openpyxl import Workbook, load_workbook

measurement_event = asyncio.Event()

# Konfiguration
DEVICE_ADDRESS = "A4:C1:38:A5:20:BB"  # <- anpassen, falls nötig
CHAR_UUID = "00002a35-0000-1000-8000-00805f9b34fb"
EXCEL_FILE = "log.xlsx"

# Robuster Parser nach Bluetooth-Spezifikation
def parse_measurement(data: bytes):
    try:
        flags = data[0]
        index = 1

        units_kpa = bool(flags & 0x01)
        timestamp_present = bool(flags & 0x02)
        pulse_present = bool(flags & 0x04)
        user_present = bool(flags & 0x08)
        status_present = bool(flags & 0x10)

        # Pflichtfelder (6 Bytes)
        systolic = int.from_bytes(data[index:index+2], byteorder='little')
        index += 2
        diastolic = int.from_bytes(data[index:index+2], byteorder='little')
        index += 2
        _ = int.from_bytes(data[index:index+2], byteorder='little')  # MAP ignorieren
        index += 2

        # Berechne MAP immer selbst
        map_val = diastolic + (systolic - diastolic) / 3

        if units_kpa:
            # Umrechnung von kPa in mmHg
            systolic = round(systolic * 7.50062)
            diastolic = round(diastolic * 7.50062)
            map_val = map_val * 7.50062

        # MAP auf zwei Nachkommastellen runden
        map_val = round(map_val, 2)

        # Zeitstempel vorhanden?
        if timestamp_present:
            year = int.from_bytes(data[index:index+2], byteorder='little')
            month = data[index+2]
            day = data[index+3]
            hour = data[index+4]
            minute = data[index+5]
            second = data[index+6]
            timestamp = f"{year:04}-{month:02}-{day:02} {hour:02}:{minute:02}:{second:02}"
            index += 7
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Puls vorhanden?
        if pulse_present:
            pulse = int.from_bytes(data[index:index+2], byteorder='little')
            index += 2
        else:
            pulse = None

        # User ID – optional
        if user_present:
            index += 1

        # Status – optional
        if status_present:
            index += 2

        return {
            "timestamp": timestamp,
            "systole": systolic,
            "diastole": diastolic,
            "map": map_val,
            "pulse": pulse
        }

    except Exception as e:
        print(f"❌ Parser-Fehler: {e}")
        return None

# Excel-Schreiber
def write_to_excel(values):
    path = os.path.join(os.path.dirname(__file__), EXCEL_FILE)
    headers = ["Zeitstempel", "Systole", "Diastole", "MAP", "Puls"]

    if not os.path.exists(path):
        wb = Workbook()
        ws = wb.active
        ws.title = "Messwerte"
        ws.append(headers)
    else:
        wb = load_workbook(path)
        ws = wb.active

    ws.append([
        values["timestamp"],
        values["systole"],
        values["diastole"],
        values["map"],
        values["pulse"] if values["pulse"] is not None else ""
    ])

    wb.save(path)
    print(f"✅ Gespeichert: {values}")

# BLE-Callback bei Benachrichtigung
def handle_notification(sender, data):
    print(f"\n🔵 Empfangene Daten von {sender}")
    print(f"Raw: {data.hex()}")
    values = parse_measurement(data)
    if values:
        write_to_excel(values)
        measurement_event.set()

async def log_once(client):
    measurement_event.clear()
    print("📡 Warte auf Messdaten (60 Sekunden)...")
    await client.start_notify(CHAR_UUID, handle_notification)
    try:
        await asyncio.wait_for(measurement_event.wait(), timeout=60)
    except asyncio.TimeoutError:
        print("⚠️  Kein Messwert empfangen (Timeout)")
    await client.stop_notify(CHAR_UUID)
    print("🛑 Messzyklus beendet")

# Haupt-Async-Logik
async def main():
    while True:
        print("🔍 Suche nach Beurer BM64 ...")
        device = await BleakScanner.find_device_by_address(DEVICE_ADDRESS, timeout=10.0)
        if not device:
            print("⌛ Gerät nicht gefunden, neuer Versuch in 5s")
            await asyncio.sleep(5)
            continue

        try:
            async with BleakClient(device) as client:
                if client.is_connected:
                    print("✅ Verbunden mit Beurer BM64")
                    await log_once(client)
                else:
                    print("❌ Verbindung fehlgeschlagen")
        except Exception as e:
            print(f"❌ Verbindungsfehler: {e}")

        print("⌛ Warte auf nächste Messung...")
        await asyncio.sleep(5)

# Einstiegspunkt
if __name__ == "__main__":
    asyncio.run(main())
