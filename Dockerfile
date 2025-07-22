# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required by Selenium and Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Add Google's official GPG key
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -

# Add the Google Chrome repository to the system's sources list
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'

# Update the package list again and install Google Chrome Stable
RUN apt-get -y update
RUN apt-get install -y google-chrome-stable

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed Python packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# --- FINAL AND CORRECT COMMAND ---
# Render এর চাহিদা অনুযায়ী পোর্ট 8080 ব্যবহার করা হচ্ছে
# এবং gunicorn কে আপনার keep_alive ফাইলটি চালানোর জন্য নির্দেশ দেওয়া হচ্ছে
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "keep_alive:app"]
