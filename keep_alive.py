from flask import Flask
from threading import Thread
import logging

# Flask এর নিজস্ব লগিং নিষ্ক্রিয় করার জন্য এই লাইনগুলো যোগ করা হয়েছে
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def home():
    # এই ফাংশনটি এখন কোনো লগ প্রিন্ট করবে না, শুধু একটি উত্তর পাঠাবে
    return "I'm alive"

def run():
  # Dockerfile অনুযায়ী পোর্ট 10000 ব্যবহার করা হচ্ছে
  app.run(host='0.0.0.0',port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()
