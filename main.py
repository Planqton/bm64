import asyncio
from bleak import BleakClient
from datetime import datetime
import os
from openpyxl import Workbook, load_workbook

# Konfiguration
DEVICE_ADDRESS = "A4:C1:38:A5:20:BB"  # <- anpassen, falls nötig
CHAR_UUID = "00002a35-0000-1000-8000-00805f9b34fb"
EXCEL_FILE = "log.xlsx"

# Robuster Parser nach Bluetooth-Spezifikation
def parse_measurement(data: bytes):
    try:
        flags = data[0]
        index = 1

        # Pflichtfelder (6 Bytes)
        systolic = int.from_bytes(data[index:index+2], byteorder='little')
        index += 2
        diastolic = int.from_bytes(data[index:index+2], byteorder='little')
        index += 2
        _ = int.from_bytes(data[index:index+2], byteorder='little')  # MAP ignorieren
        index += 2

        # Berechne MAP immer selbst
        map_val = int(diastolic + (systolic - diastolic) / 3)

        # Zeitstempel (Bit 0)
        if flags & 0x01:
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

        # Puls (Bit 1)
        if flags & 0x02:
            pulse = int.from_bytes(data[index:index+2], byteorder='little')
            index += 2
        else:
            pulse = None

        # User ID (Bit 2) – optional
        if flags & 0x04:
            index += 1

        # Status (Bit 3) – optional
        if flags & 0x08:
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

# Haupt-Async-Logik
async def main():
    async with BleakClient(DEVICE_ADDRESS) as client:
        if client.is_connected:
            print("✅ Verbunden mit Beurer BM64")
        else:
            print("❌ Verbindung fehlgeschlagen")
            return

        print("📡 Warte auf Messdaten (60 Sekunden)...")
        await client.start_notify(CHAR_UUID, handle_notification)
        await asyncio.sleep(60)
        await client.stop_notify(CHAR_UUID)
        print("🛑 Fertig.")

# Einstiegspunkt
if __name__ == "__main__":
    asyncio.run(main())
