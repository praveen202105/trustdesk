# Free demo hosting: same services/processes, one externally exposed container.
FROM node:24-bookworm-slim AS web-build
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 && rm -rf /var/lib/apt/lists/*
COPY --from=web-build /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY backend/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r requirements.lock && useradd --uid 10001 --create-home app
COPY backend /app
COPY capstone/data /data
COPY --from=web-build /web/.next/standalone /web
COPY --from=web-build /web/.next/static /web/.next/static
COPY deploy/free_host.py /app/free_host.py
ENV DATA_DIR=/data PYTHONUNBUFFERED=1 HOSTNAME=0.0.0.0 PORT=10000
USER app
EXPOSE 10000
CMD ["python", "/app/free_host.py"]
