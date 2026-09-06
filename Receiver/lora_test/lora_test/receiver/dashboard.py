from flask import Flask
import json

app = Flask(__name__)

@app.route('/')

def home():

    with open("live_data.json", "r") as f:

        data = json.load(f)

    return f"""

    <html>

    <head>

        <title>LoRa Dashboard</title>

        <meta http-equiv="refresh" content="1">

        <style>

            body {{

                background-color: #0f172a;
                color: white;
                font-family: Arial;
                padding: 40px;
            }}

            h1 {{

                color: #38bdf8;
            }}

            .card {{

                background-color: #1e293b;
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 10px;
                width: 420px;
            }}

            .value {{

                font-size: 24px;
                color: #22c55e;
            }}

            a {{

                color: #38bdf8;
                text-decoration: none;
            }}

        </style>

    </head>

    <body>

        <h1>LoRa Live Dashboard</h1>

        <div class="card">

            <h2>RSSI</h2>

            <div class="value">
                {data['rssi']} dBm
            </div>

        </div>

        <div class="card">

            <h2>SNR</h2>

            <div class="value">
                {data['snr']} dB
            </div>

        </div>

        <div class="card">

            <h2>Packets Received</h2>

            <div class="value">
                {data['packets']}
            </div>

        </div>

        <div class="card">

            <h2>Transmission Time</h2>

            <div class="value">
                {data['tx_time']:.2f} sec
            </div>

        </div>

        <div class="card">

            <h2>Transmitter Location</h2>

            <div class="value">

                Latitude :
                {data['tx_lat']}

                <br><br>

                Longitude :
                {data['tx_lon']}

                <br><br>

                <a target="_blank"
                href="
                https://maps.google.com/?q=
                {data['tx_lat']},
                {data['tx_lon']}
                ">

                Open TX Location in Google Maps

                </a>

            </div>

        </div>

        <div class="card">

            <h2>Receiver Location</h2>

            <div class="value">

                Latitude :
                {data['rx_lat']}

                <br><br>

                Longitude :
                {data['rx_lon']}

                <br><br>

                <a target="_blank"
                href="
                https://maps.google.com/?q=
                {data['rx_lat']},
                {data['rx_lon']}
                ">

                Open RX Location in Google Maps

                </a>

            </div>

        </div>

    </body>

    </html>

    """

if __name__ == '__main__':

    app.run(
        host='0.0.0.0',
        port=5000
    )
