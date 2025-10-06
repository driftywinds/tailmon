FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Create data directory for state persistence
RUN mkdir -p /data

CMD ["python3", "-u", "main.py"]
