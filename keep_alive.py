from flask import Flask
from threading import Thread
import subprocess

app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# main.py ফাইল অটো চালু করা হচ্ছে
def run_main():
    subprocess.Popen(["python", "main.py"])

# Flask চালু + main.py চালু
if __name__ == "__main__":
    keep_alive()
    run_main()
