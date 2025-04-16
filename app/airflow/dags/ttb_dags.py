import requests
from datetime import datetime, timedelta
import sys
import os
import time
import logging
from bs4 import BeautifulSoup
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
from app.core.config import settings
from sqlalchemy.sql import text

# Ensure the DATABASE_URL is correctly set
DATABASE_URL = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
logger.info(f"Connecting to database at {DATABASE_URL}")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_start_period():
    logger.info("Determining start period")
    session = SessionLocal()
    try:
        row_count = session.execute(text("SELECT COUNT(*) FROM exchange_rates WHERE bank_id = 5")).scalar()
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

def insert_exchange_rates(data, date):
    logger.info(f"Inserting exchange rates for {date} into the database")
    session = SessionLocal()
    try:
        if data:
            row = data[0]
            currency_code = row['currency']
            if currency_code == 'USDUnited States Dollar':
                currency_code = 'USD'
            if currency_code != 'USD':
                return
            try:
                selling_rate = float(row['selling_rate'].strip())
                buying_rate = float(row['buying_rate'].strip())
            except ValueError:
                logger.warning(f"Invalid rates for {currency_code} on {date}: {row}")
                return
            bank_id = 5

            currency_map = {
                'USD': 1,  
                'THB': 2  
            }
            
            base_currency_id = currency_map.get(currency_code, None)
            target_currency_id = currency_map.get('THB', None)

            if base_currency_id is None:
                return

            # Check if the bank ID exists in the banks table
            bank_exists = session.execute(
                text("SELECT 1 FROM banks WHERE id = :bank_id"),
                {'bank_id': bank_id}
            ).scalar()
            if not bank_exists:
                logger.error(f"Bank ID {bank_id} does not exist in the banks table")
                return

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

def fetch_exchange_rates(date):
    url = f"https://www.ttbbank.com/th/rates/exchange-rates?dateCurrent={date}"
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9,th;q=0.8",
        "cache-control": "max-age=0",
        "referer": f"https://www.ttbbank.com/th/rates/exchange-rates?dateCurrent={date}",
        "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find("table")
        if table:
            rows = table.find_all("tr")
            data = []
            for row in rows[1:]:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    currency = cols[0].text.strip()
                    buying_rate = cols[1].text.strip()
                    selling_rate = cols[2].text.strip()
                    data.append({
                        "currency": currency,
                        "buying_rate": buying_rate,
                        "selling_rate": selling_rate
                    })
            return data
        else:
            logger.warning("No table found in the response.")
            return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching exchange rates: {e}")
        send_notification(
            "TTB Exchange Rates Unavailable",
            f"Failed to fetch TTB exchange rates for {date}. Error: {e}"
        )
        return []

def process_exchange_rates():
    start_period = get_start_period()

    if start_period != datetime.today().strftime('%Y-%m-%d'):
        start_date = datetime.strptime(start_period, '%Y-%m-%d')
        end_date = datetime.today()
        delta = timedelta(days=1)

        while start_date <= end_date:
            date_str = start_date.strftime('%m%d%Y')
            logger.info(f"Processing date: {date_str}")
            data = fetch_exchange_rates(date_str)
            if data:
                insert_exchange_rates(data, start_date.strftime('%Y-%m-%d'))
            else:
                logger.warning(f"No data fetched for {date_str}")
            start_date += delta
    else:
        date_str = datetime.today().strftime('%m%d%Y')
        logger.info(f"Processing date: {date_str}")
        data = fetch_exchange_rates(date_str)
        if data:
            insert_exchange_rates(data, datetime.today().strftime('%Y-%m-%d'))
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
    'ttb_exchange_rates',
    default_args=default_args,
    description='Fetch and insert TTB exchange rates daily',
    schedule_interval=timedelta(days=1),
    catchup=False,
)

task = PythonOperator(
    task_id='process_exchange_rates',
    python_callable=process_exchange_rates,
    dag=dag,
)
