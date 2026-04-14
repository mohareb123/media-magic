FROM python:3.12-slim

# Install ffmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory to parent so bot/ is a proper package
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt /app/bot/requirements.txt
RUN pip install --no-cache-dir -r /app/bot/requirements.txt

# Copy bot source code into /app/bot/
COPY . /app/bot/

# Create directories for data and downloads
RUN mkdir -p /app/bot/data /app/bot/downloads /app/bot/logs

# Set environment variable placeholder
ENV TELEGRAM_BOT_TOKEN=""

# Run the bot from the parent directory so 'bot' is a package
CMD ["python", "-m", "bot.main"]
