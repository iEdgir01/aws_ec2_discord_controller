# Enhanced EC2 Discord Controller Bot - Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ec2bot/ ./ec2bot/
COPY bot.py .
COPY functions.py .
COPY api.py .

# Create data directory
RUN mkdir -p /data && chmod 755 /data

# Run as non-root user for security
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app /data

USER botuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/data/ec2bot.db') else 1)"

# Run the bot
CMD ["python", "-u", "bot.py"]
