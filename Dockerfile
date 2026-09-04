FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright and XML parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project requirements
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN python -m playwright install --with-deps chromium

# Copy application source
COPY src/ ./src/
COPY doc/ ./doc/

EXPOSE 8080

CMD ["python", "src/dashboard/server.py"]
