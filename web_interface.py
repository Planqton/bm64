from flask import Flask, render_template_string
import asyncio
from bleak import BleakScanner

app = Flask(__name__)


@app.route("/")
def index():
    devices = asyncio.run(BleakScanner.discover(timeout=5.0))
    options = "".join(
        f'<option value="{d.address}">{d.name or d.address} ({d.address})</option>'
        for d in devices
    )
    html = f"""
    <html>
    <head><title>Bluetooth Geraete</title></head>
    <body>
        <h1>Verfuegbare Bluetooth Geraete</h1>
        <form>
            <select name='device'>
                {options}
            </select>
        </form>
    </body>
    </html>
    """
    return render_template_string(html)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
