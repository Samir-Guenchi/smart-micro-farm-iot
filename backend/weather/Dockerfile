FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY weather.py .
VOLUME /app/logs
ENV DECISION_LOG=/app/logs/decisions.jsonl
CMD ["python", "-u", "weather.py"]
