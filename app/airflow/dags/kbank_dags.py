import requests
from datetime import datetime, timedelta
import sys
import os
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
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_start_period():
    session = SessionLocal()
    try:
        row_count = session.execute(text("SELECT COUNT(*) FROM exchange_rates WHERE bank_id = 3")).scalar()
        if row_count == 0:
            start_period = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
        else:
            start_period = datetime.today().strftime('%Y-%m-%d')
    except Exception as e:
        start_period = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    finally:
        session.close()
    return start_period

def insert_exchange_rates(data, date):
    session = SessionLocal()
    try:
        if data:
            currency_code = data['data-lname']
            if currency_code != 'USD : 1':
                return
            currency_code = 'USD'
            try:
                selling_rate = float(data['data-sellbn'].strip())
                buying_rate = float(data['data-buybn'].strip())
            except ValueError:
                return
            bank_id = 3

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
            else:
                pass
    except Exception as e:
        session.rollback()
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
    except Exception as e:
        pass

def fetch_exchange_rates(date):
    url = "https://www.kasikornbank.com/en/rate/pages/Foreign-Exchange.aspx"
    params = {
        "d": date.day,
        "m": date.month,
        "y": date.year,
        "r": 0,
    }
    headers = {
        "Accept": "text/plain, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9,th;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://www.kasikornbank.com",
        "Referer": "https://www.kasikornbank.com/en/rate/pages/foreign-exchange.aspx",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    }
    try:
        response = requests.post(url, params=params, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        rate_div = soup.find("div", id="divRate", attrs={"data-date": date.strftime('%d %B %Y')})
        if rate_div:
            items = rate_div.find_all("div", class_="itemsRate")
            for item in items:
                data_lname = item.get("data-lname", "").strip()
                if "USD : 1" in data_lname:
                    currency_data = {
                        "data-lname": data_lname,
                        "data-buybn": item.get("data-buybn", "").strip(),
                        "data-sellbn": item.get("data-sellbn", "").strip(),
                        "data-buyexp": item.get("data-buyexp", "").strip(),
                        "data-sellchq": item.get("data-sellchq", "").strip(),
                    }
                    return currency_data
            logging.warning(f"Currency 'USD : 1' not found in id='divRate'.")
            return None
        else:
            logging.warning("No divRate found in the response.")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching exchange rates: {e}")
        return None

def process_exchange_rates():
    start_period = get_start_period()
    end_date = datetime.today()
    start_date = datetime.strptime(start_period, '%Y-%m-%d')

    while start_date <= end_date:
        date_str = start_date.strftime('%Y-%m-%d')
        logger.info(f"Processing date: {date_str}")
        data = fetch_exchange_rates(start_date)
        if data:
            insert_exchange_rates(data, date_str)
        else:
            logger.warning(f"No data fetched for {date_str}")
        start_date += timedelta(days=1)

default_args = {
    'owner': 'domwatcharin',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'kbank_exchange_rates',
    default_args=default_args,
    description='A DAG to fetch and store exchange rates daily',
    schedule_interval=timedelta(days=1),
    catchup=False,
)

fetch_exchange_rates_task = PythonOperator(
    task_id='fetch_exchange_rates',
    python_callable=process_exchange_rates,
    dag=dag,
)

fetch_exchange_rates_task
