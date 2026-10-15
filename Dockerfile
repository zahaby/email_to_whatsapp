FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY email_to_whatsapp ./email_to_whatsapp
ENV STATE_FILE=/data/state.json PYTHONUNBUFFERED=1
VOLUME /data
CMD ["python", "-m", "email_to_whatsapp"]
