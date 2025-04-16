# Deployment Guide for AWS EC2

## Prerequisites

- AWS account
- AWS CLI installed and configured
- EC2 instance with Docker and Docker Compose installed

## Steps

### 1. Launch an EC2 Instance

1. Log in to the AWS Management Console.
2. Navigate to the EC2 Dashboard.
3. Click on "Launch Instance".
4. Choose an Amazon Machine Image (AMI). For example, select "Amazon Linux 2 AMI".
5. Choose an instance type. For example, select "t2.micro" for free tier eligibility.
6. Configure instance details as needed.
7. Add storage if necessary.
8. Add tags if necessary.
9. Configure security group:
   - Add a rule to allow SSH (port 22) from your IP.
   - Add a rule to allow HTTP (port 80) from anywhere.
   - Add a rule to allow HTTPS (port 443) from anywhere.
10. Review and launch the instance.
11. Download the key pair (.pem file) and keep it safe.

### 2. Connect to the EC2 Instance

1. Open a terminal on your local machine.
2. Connect to the EC2 instance using SSH:

   ```sh
   ssh -i /path/to/your-key-pair.pem ec2-user@your-ec2-public-ip
   ```

### 3. Install Docker and Docker Compose

1. Update the package index:

   ```sh
   sudo yum update -y
   ```

2. Install Docker:

   ```sh
   sudo amazon-linux-extras install docker -y
   ```

3. Start Docker:

   ```sh
   sudo service docker start
   ```

4. Add the `ec2-user` to the `docker` group:

   ```sh
   sudo usermod -aG docker ec2-user
   ```

5. Log out and log back in to apply the group membership.

6. Install Docker Compose:

   ```sh
   sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

### 4. Clone the Repository

1. Clone your repository:

   ```sh
   git clone https://github.com/DomWatcharin/Currency-Exchange.git
   cd Currency-Exchange
   ```

### 5. Set Up Environment Variables

1. Create a `.env` file with the necessary environment variables:

   ```sh
   touch .env
   ```

2. Add the following content to the `.env.production` file:

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

   email=mock_email_password
   sender_email=mock_sender_email@example.com
   receiver_email=mock_receiver_email@example.com
   ```

### 6. Set Environment to Production

1. Set the environment to production:

   ```sh
   make set-env-prod
   ```

### 7. Build and Start the Docker Containers

1. Build the Docker images:

   ```sh
   make build
   ```

2. Start the Docker containers:

   ```sh
   make up
   ```

### 8. Access the Services

- API: `http://your-ec2-public-ip/api`
- Airflow: `http://your-ec2-public-ip/airflow`
- Streamlit: `http://your-ec2-public-ip/streamlit`

### 9. Monitor and Manage the Services

- To view logs:

  ```sh
  make logs
  ```

- To stop the services:

  ```sh
  make down
  ```

- To restart the services:

  ```sh
  make restart
  ```

### 10. Security Considerations

- Ensure that your security groups are configured correctly to allow only necessary traffic.
- Regularly update your EC2 instance and Docker images to apply security patches.
- Use IAM roles and policies to manage access to AWS resources securely.
