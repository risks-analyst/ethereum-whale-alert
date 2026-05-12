import os
import time
import threading
import requests
from flask import Flask, render_template, jsonify
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

RPC_URL = os.getenv("RPC_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
MIN_ETH = float(os.getenv("MIN_ETH_THRESHOLD", 100))

w3 = Web3(Web3.HTTPProvider(RPC_URL))

whale_alerts = []

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message})

def monitor_blocks():
    last_block = w3.eth.block_number
    while True:
        try:
            current_block = w3.eth.block_number
            if current_block > last_block:
                block = w3.eth.get_block(current_block, full_transactions=True)
                for tx in block.transactions:
                    eth_value = w3.from_wei(tx["value"], "ether")
                    if eth_value >= MIN_ETH:
                        alert = {
                            "hash": tx["hash"].hex(),
                            "from": tx["from"],
                            "to": tx["to"],
                            "value_eth": float(eth_value),
                            "block": current_block
                        }
                        whale_alerts.insert(0, alert)
                        if len(whale_alerts) > 50:
                            whale_alerts.pop()
                        msg = (
                            f"🐋 WHALE ALERT\n"
                            f"Value: {eth_value:.2f} ETH\n"
                            f"From: {tx['from']}\n"
                            f"To: {tx['to']}\n"
                            f"Hash: {tx['hash'].hex()}"
                        )
                        send_telegram(msg)
                last_block = current_block
            time.sleep(12)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(12)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/alerts")
def alerts():
    return jsonify(whale_alerts)

if __name__ == "__main__":
    monitor = threading.Thread(target=monitor_blocks, daemon=True)
    monitor.start()
    app.run(host="0.0.0.0", port=5001, debug=False)
