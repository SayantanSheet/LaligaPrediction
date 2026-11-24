FROM python:3.12-slim

WORKDIR /app/backend

# libgomp is required at runtime by LightGBM / XGBoost
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

# Bake the trained model into the image so the server starts in well under a second.
RUN python -m app.ml.train

EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
