FROM python:3.9-slim

WORKDIR /app

# Install PostgreSQL client
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Gunicorn
RUN pip install gunicorn

COPY scripts/create_admin_user.py /app/scripts/create_admin_user.py
COPY scripts/entrypoint.sh /app/scripts/entrypoint.sh
COPY scripts/wait-for-it.sh /app/scripts/wait-for-it.sh
COPY scripts/init-db.sh /docker-entrypoint-initdb.d/init-db.sh
RUN chmod +x /app/scripts/entrypoint.sh /app/scripts/wait-for-it.sh /docker-entrypoint-initdb.d/init-db.sh

COPY . .

# Install Gunicorn
RUN pip install gunicorn

# Copy application files
COPY . /app

# Expose the API port
EXPOSE 8000

ENV PYTHONPATH=/app:/opt/airflow/dags:/opt/airflow

CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]