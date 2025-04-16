# Currency Exchange API

## Setup Instructions

### Prerequisites

- Docker
- Docker Compose
- Python 3.8+
- pip

### Environment Setup

1. Clone the repository:

   ```sh
   git clone https://github.com/DomWatcharin/Currency-Exchange.git
   cd Currency-Exchange
   ```

2. Create environment files:

   - `.env.development`
   - `.env.production`

   Example content for `.env.development`:

   ```env
   POSTGRES_USER=test_user
   POSTGRES_PASSWORD=test_password
   POSTGRES_DB=exchange_rates
   POSTGRES_HOST=db
   POSTGRES_PORT=5432

   REDIS_HOST=redis
   REDIS_PORT=6379

   API_PORT=8000

   ADMIN_API_KEY=your_admin_api_key
   USER_API_KEY=your_user_api_key

   AIRFLOW_FERNET_KEY=your_fernet_key
   AIRFLOW_PORT=8080

   STREAMLIT_PORT=8501

   SECRET_KEY=your_secret_key

   email=your_app_password
   sender_email=your_sender_email
   receiver_email=your_receiver_email
   ```

   Example content for `.env.production`:

   ```env
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_DB=exchange_rates
   POSTGRES_HOST=db
   POSTGRES_PORT=5432

   REDIS_HOST=redis
   REDIS_PORT=6379

   API_PORT=8000

   ADMIN_API_KEY=your_admin_api_key
   USER_API_KEY=your_user_api_key

   AIRFLOW_FERNET_KEY=your_fernet_key
   AIRFLOW_PORT=8080

   STREAMLIT_PORT=8501

   SECRET_KEY=your_secret_key

   email=your_app_password
   sender_email=your_sender_email
   receiver_email=your_receiver_email
   ```

### Docker Setup

1. Set environment to development:

   ```sh
   make set-env-dev
   ```

2. Build the Docker images:

   ```sh
   make build
   ```

3. Build and start the Docker containers:

   ```sh
   make up
   ```

4. To stop the Docker containers:

   ```sh
   make down
   ```

5. To restart the Docker containers:

   ```sh
   make restart
   ```

### Nginx Setup

1. Add Nginx configuration to the `nginx` directory:

   ```sh
   mkdir -p nginx/conf.d
   ```

2. Create a file named `default.conf` in the `nginx/conf.d` directory with the following content:

   ```nginx
   upstream api {
      server api:8000;
   }

   upstream streamlit {
      server streamlit:8501;
   }

   upstream airflow {
      server airflow:8080;
   }

   server {
      listen 80;
      server_name api.localhost;

      location / {
         proxy_pass http://api;
         proxy_set_header Host $host;
         proxy_set_header X-Real-IP $remote_addr;
         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
         proxy_set_header X-Forwarded-Proto $scheme;
         proxy_read_timeout 90;
         proxy_connect_timeout 90;
         proxy_redirect off;
      }

      error_page 502 /502.html;
      location = /502.html {
         internal;
         root /usr/share/nginx/html;
      }
   }

   server {
      listen 80;
      server_name streamlit.localhost;

      location / {
         proxy_pass http://streamlit;
         proxy_set_header Host $host;
         proxy_set_header X-Real-IP $remote_addr;
         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
         proxy_set_header X-Forwarded-Proto $scheme;
         proxy_read_timeout 90;
         proxy_connect_timeout 90;
         proxy_redirect off;

         # Handle WebSocket connections
         proxy_http_version 1.1;
         proxy_set_header Upgrade $http_upgrade;
         proxy_set_header Connection "upgrade";
      }

      error_page 502 /502.html;
      location = /502.html {
         internal;
         root /usr/share/nginx/html;
      }
   }

   server {
      listen 80;
      server_name airflow.localhost;

      location / {
         proxy_pass http://airflow;
         proxy_set_header Host $host;
         proxy_set_header X-Real-IP $remote_addr;
         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
         proxy_set_header X-Forwarded-Proto $scheme;
         proxy_read_timeout 90;
         proxy_connect_timeout 90;
         proxy_redirect off;
      }

      error_page 502 /502.html;
      location = /502.html {
         internal;
         root /usr/share/nginx/html;
      }
   }
   ```

3. Add Nginx service to `docker-compose.yml`:

   ```yaml
   services:
     # ...existing code...

     nginx:
       image: nginx:latest
       ports:
         - "80:80"
       volumes:
         - ./nginx/conf.d:/etc/nginx/conf.d
       depends_on:
         - api
         - airflow-webserver
         - streamlit
       networks:
         - app-network

   networks:
     app-network:
       driver: bridge

   volumes:
     pgdata:
   ```

### Running Tests

1. Run tests using pytest:

   ```sh
   make test
   ```

### Database Migrations

1. Run database migrations:

   ```sh
   make migrate
   ```

### API Documentation

The API documentation is available at `http://localhost/api/docs` when the server is running.

### Airflow

The Airflow web interface is available at `http://localhost/airflow`.

### Streamlit

The Streamlit app is available at `http://localhost/streamlit`.

### Deployment Guide

Refer to the `DEPLOYMENT.md` file for cloud platform deployment instructions.