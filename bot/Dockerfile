FROM python:3.12-slim

# Install ffmpeg and Playwright system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
        libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
        libpango-1.0-0 libcairo2 libasound2 libxshmfence1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory to parent so bot/ is a proper package
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt /app/bot/requirements.txt
RUN pip install --no-cache-dir -r /app/bot/requirements.txt && \
    python -m playwright install chromium

# Copy bot source code into /app/bot/
COPY . /app/bot/

# Create directories for data and downloads
RUN mkdir -p /app/bot/data /app/bot/downloads /app/bot/logs

# Set environment variable placeholders
ENV TELEGRAM_BOT_TOKEN=""
ENV COOKIES_FILE=""
ENV POT_SERVER_URL=""
ENV BROWSER_COOKIES_ENABLED="true"

# Run the bot from the parent directory so 'bot' is a package
CMD ["python", "-m", "bot.main"]
