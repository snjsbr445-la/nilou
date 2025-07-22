FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y wget gnupg

RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
RUN apt-get -y update
RUN apt-get install -y google-chrome-stable

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Gunicorn দিয়ে Flask চালাবে, কিন্তু log-level কমিয়ে দিবে
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--log-level", "critical", "--access-logfile", "/dev/null", "--error-logfile", "/dev/null", "keep_alive:app"]
