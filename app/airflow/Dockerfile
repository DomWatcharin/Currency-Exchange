FROM apache/airflow:2.10.4

# Install any additional dependencies if needed
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

USER airflow

# Copy the Airflow configuration files
# COPY config/airflow.cfg /opt/airflow/airflow.cfg

# Set the working directory
WORKDIR /opt/airflow

# Expose the port
EXPOSE 8080

# Set the PYTHONPATH
ENV PYTHONPATH="/opt/airflow/app:/opt/airflow"

# Set the entrypoint
ENTRYPOINT ["/entrypoint"]

# Default command
CMD ["webserver"]
