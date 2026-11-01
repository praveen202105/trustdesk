FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r requirements.lock && useradd --uid 10001 --create-home app && mkdir -p /reports && chown app:app /reports
COPY backend /app
COPY capstone/data /data
ENV DATA_DIR=/data
USER app
CMD ["sh","-c","exec uvicorn trustdesk.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
