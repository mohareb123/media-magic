FROM python:3.12-slim

# Install ffmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot source code
COPY . .

# Create directories for data and downloads
RUN mkdir -p data downloads logs

# Set environment variable placeholder
ENV TELEGRAM_BOT_TOKEN=""

# Run the bot
CMD ["python", "-m", "bot.main"]
