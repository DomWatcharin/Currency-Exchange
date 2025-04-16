import http.client
import gzip
from io import BytesIO
from datetime import datetime, timedelta
import pandas as pd
import json
import sys
import os
import logging
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to the sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from app.core.config import settings

# Ensure the DATABASE_URL is correctly set
DATABASE_URL = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
logger.info(f"Connecting to database at {DATABASE_URL}")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def send_notification(subject, body):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = os.getenv("sender_email")
    receiver_email = os.getenv("receiver_email")
    password = os.getenv("email")

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.close()
        logger.info("Notification email sent successfully")
    except Exception as e:
        logger.error(f"Failed to send notification email: {e}")

def fetch_daily_avg_exg_rate(start_period, end_period, currency):
    conn = http.client.HTTPSConnection("apigw1.bot.or.th")
    headers = { 'X-IBM-Client-Id': "0d12f7e1-7cc1-4af5-990a-269c52de46a3" }
    url = f"/bot/public/Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE/?start_period={start_period}&end_period={end_period}&currency={currency}"
    conn.request("GET", url, headers=headers)
    res = conn.getresponse()
    data = res.read()

    if res.getheader('Content-Encoding') == 'gzip':
        buf = BytesIO(data)
        f = gzip.GzipFile(fileobj=buf)
        data = f.read()

    return data.decode("utf-8")

def json_to_dataframe(json_data):
    data = json.loads(json_data)
    data_detail = data['result']['data']['data_detail']
    
    df = pd.DataFrame(data_detail)
    df = df.rename(columns={
        'period': 'date',
        'currency_id': 'base_currency_id',
        'selling': 'selling_rate',
        'buying_transfer': 'buying_rate'
    })
    df['bank_id'] = 1 
    df['target_currency_id'] = 'THB'  
    df = df[['date', 'base_currency_id', 'target_currency_id', 'selling_rate', 'buying_rate', 'bank_id']]
    
    currency_map = {
        'USD': 1,  
        'THB': 2  
    }
    df['base_currency_id'] = df['base_currency_id'].map(currency_map)
    df['target_currency_id'] = df['target_currency_id'].map(currency_map)
    
    return df

def insert_exchange_rates(df):
    session = SessionLocal()
    try:
        for index, row in df.iterrows():
            if not row['date']:
                logger.warning(f"Skipping row with empty date: {row}")
                continue

            bank_exists = session.execute(
                text("SELECT 1 FROM banks WHERE id = :bank_id"),
                {'bank_id': row['bank_id']}
            ).scalar()
            if not bank_exists:
                logger.error(f"Bank ID {row['bank_id']} does not exist")
                continue

            exists = session.execute(
                text("SELECT 1 FROM exchange_rates WHERE date = :date AND bank_id = :bank_id"),
                {'date': row['date'], 'bank_id': row['bank_id']}
            ).scalar()
            if not exists:
                session.execute(
                    text("""
                        INSERT INTO exchange_rates (date, base_currency_id, target_currency_id, selling_rate, buying_rate, bank_id)
                        VALUES (:date, :base_currency_id, :target_currency_id, :selling_rate, :buying_rate, :bank_id)
                    """),
                    {
                        'date': row['date'],
                        'base_currency_id': row['base_currency_id'],
                        'target_currency_id': row['target_currency_id'],
                        'selling_rate': row['selling_rate'],
                        'buying_rate': row['buying_rate'],
                        'bank_id': row['bank_id']
                    }
                )
                session.commit()
                logger.info(f"Successfully inserted exchange rates for {row['date']}")
            else:
                logger.info(f"Exchange rates for {row['date']} already exist")
    except Exception as e:
        session.rollback()
        logger.error(f"Error inserting data: {e}")
    finally:
        session.close()

def process_exchange_rates():
    end_date = datetime.today()
    start_date = end_date - timedelta(days=30)
    currency = "USD"

    while start_date <= end_date:
        # if start_date.weekday() >= 5:  # Skip Saturday and Sunday
        #     start_date += timedelta(days=1)
        #     continue

        date_str = start_date.strftime('%Y-%m-%d')
        logger.info(f"Processing date: {date_str}")

        session = SessionLocal()
        exists = session.execute(
            text("SELECT 1 FROM exchange_rates WHERE date = :date AND bank_id = 1"),
            {'date': date_str}
        ).scalar()
        session.close()

        if not exists:
            exchange_rate_data = fetch_daily_avg_exg_rate(date_str, date_str, currency)
            if exchange_rate_data:
                df = json_to_dataframe(exchange_rate_data)
                df = df.sort_values(by='date').reset_index(drop=True)
                insert_exchange_rates(df)
        else:
            logger.info(f"Exchange rates for {date_str} already exist")

        start_date += timedelta(days=1)

default_args = {
    'owner': 'domwatcharin',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'bot_exchange_rates',
    default_args=default_args,
    description='Fetch and insert BOT exchange rates daily',
    schedule_interval=timedelta(days=1),
    catchup=False,
)

task = PythonOperator(
    task_id='process_exchange_rates',
    python_callable=process_exchange_rates,
    dag=dag,
)
