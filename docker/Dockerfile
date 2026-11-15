# specifies the base image
FROM python:3.11-slim

# sets environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Sets the working directory inside the container
WORKDIR /app

# copy the requirements file from the local system to the container
COPY requirements-docker.txt .

# Executes the command while building the image
RUN pip install --no-cache-dir -r requirements-docker.txt

# code, trained model and zip-prefix coordinates
COPY src/ src/
COPY app/ app/
COPY models/delivery_time_regressor.joblib models/delivery_time_regressor.joblib
COPY data/processed/geo_zip.parquet data/processed/geo_zip.parquet

# run as a normal user, the logger writes to /app/logs
RUN useradd --create-home appuser && mkdir -p logs && chown -R appuser /app
USER appuser

# informs docker that the container listens on a port
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
   CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]