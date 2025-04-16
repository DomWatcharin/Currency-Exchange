import requests
import pandas as pd
from datetime import datetime, timedelta
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

def get_start_period():
    logger.info("Determining start period")
    session = SessionLocal()
    try:
        row_count = session.execute(text("SELECT COUNT(*) FROM exchange_rates WHERE bank_id = 2")).scalar()
        logger.info(f"Row count for bank_id 2: {row_count}")
        if row_count == 0:
            start_period = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
        else:
            start_period = datetime.today().strftime('%Y-%m-%d')
    except Exception as e:
        logger.error(f"Error checking row count: {e}")
        start_period = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    finally:
        session.close()
    logger.info(f"Start period: {start_period}")
    return start_period

def fetch_exchange_rates(date):
    url = "https://www.scb.co.th/services/scb/exchangeRateService/history.json"
    buddhist_year = int(date[:4]) + 543
    buddhist_date = f"{buddhist_year}{date[4:]}"
    params = {
        "_charset_": "UTF-8",
        "lang": "th",
        "page": "2ea9c13a-6fb9-4a75-9abd-87ef79ee71cc,803723e0-f125-47a3-8fc1-185fa4033af9",
        "date": buddhist_date,
        "currency": "USD"
    }
    headers = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9,th;q=0.8",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
        "referer": "https://www.scb.co.th/th/personal-banking/foreign-exchange-rates.html"
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        response_data = response.json()

        exchange_rates_df = pd.DataFrame(response_data.get('exchangeRates', []))
        exchange_rates_df['date'] = date
        return exchange_rates_df
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching exchange rates: {e}")
        send_notification(
            "SCB Exchange Rates Unavailable",
            f"Failed to fetch SCB exchange rates for {date}. Error: {e}"
        )
        return pd.DataFrame()

def insert_exchange_rates(data, date):
    logger.info(f"Inserting exchange rates for {date} into the database")
    session = SessionLocal()
    try:
        if not data.empty:
            for _, row in data.iterrows():
                if not row['date']:
                    logger.warning(f"Skipping row with empty date: {row}")
                    continue

                currency_code = row['curCode']
                if currency_code != 'USD':
                    continue
                try:
                    selling_rate = float(row['sellNotes'])
                    buying_rate = float(row['buyNotes'])
                except ValueError:
                    logger.warning(f"Invalid rates for {currency_code} on {date}: {row}")
                    continue
                bank_id = 2

                currency_map = {
                    'USD': 1,  
                    'THB': 2  
                }
                
                base_currency_id = currency_map.get(currency_code, None)
                target_currency_id = currency_map.get('THB', None)

                if base_currency_id is None:
                    continue

                # Check if the bank ID exists in the banks table
                bank_exists = session.execute(
                    text("SELECT 1 FROM banks WHERE id = :bank_id"),
                    {'bank_id': bank_id}
                ).scalar()
                if not bank_exists:
                    logger.error(f"Bank ID {bank_id} does not exist in the banks table")
                    continue

                exists = session.execute(
                    text("SELECT 1 FROM exchange_rates WHERE date = :date AND bank_id = :bank_id AND base_currency_id = :base_currency_id"),
                    {'date': date, 'bank_id': bank_id, 'base_currency_id': base_currency_id}
                ).scalar()
                if not exists:
                    insert_statement = text("""
                        INSERT INTO exchange_rates (date, base_currency_id, target_currency_id, selling_rate, buying_rate, bank_id)
                        VALUES (:date, :base_currency_id, :target_currency_id, :selling_rate, :buying_rate, :bank_id)
                    """)
                    session.execute(
                        insert_statement,
                        {
                            'date': date,
                            'base_currency_id': base_currency_id,
                            'target_currency_id': target_currency_id,
                            'selling_rate': selling_rate,
                            'buying_rate': buying_rate,
                            'bank_id': bank_id
                        }
                    )
                    session.commit()
                    logger.info(f"Successfully inserted exchange rates for {date}")
                else:
                    logger.info(f"Exchange rates for {date} already exist")
    except Exception as e:
        session.rollback()
        logger.error(f"Error inserting data: {e}")
    finally:
        session.close()

def process_exchange_rates():
    start_period = get_start_period()

    if start_period != datetime.today().strftime('%Y-%m-%d'):
        start_date = datetime.strptime(start_period, '%Y-%m-%d')
        end_date = datetime.today()
        delta = timedelta(days=1)

        while start_date <= end_date:
            date_str = start_date.strftime('%Y-%m-%d')
            logger.info(f"Processing date: {date_str}")
            data = fetch_exchange_rates(date_str)
            if not data.empty:
                insert_exchange_rates(data, date_str)
            else:
                logger.warning(f"No data fetched for {date_str}")
            start_date += delta
    else:
        date_str = datetime.today().strftime('%Y-%m-%d')
        logger.info(f"Processing date: {date_str}")
        data = fetch_exchange_rates(date_str)
        if not data.empty:
            insert_exchange_rates(data, date_str)
        else:
            logger.warning(f"No data fetched for {date_str}")

default_args = {
    'owner': 'domwatcharin',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'scb_exchange_rates',
    default_args=default_args,
    description='Fetch and insert SCB exchange rates daily',
    schedule_interval=timedelta(days=1),
    catchup=False,
)

task = PythonOperator(
    task_id='process_exchange_rates',
    python_callable=process_exchange_rates,
    dag=dag,
)
