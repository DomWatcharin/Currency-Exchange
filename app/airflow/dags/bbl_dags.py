import requests
from datetime import datetime, timedelta
import sys
import os
import time
import logging
from airflow import DAG
from airflow.operators.python_operator import PythonOperator

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

SUBSCRIPTION_KEY = "7d1b09abe2ea413cbf95b2d99782ed37"

def get_start_period():
    logger.info("Determining start period")
    session = SessionLocal()
    try:
        row_count = session.execute(text("SELECT COUNT(*) FROM exchange_rates WHERE bank_id = 4")).scalar()
        logger.info(f"Row count for bank_id 4: {row_count}")
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
        for row in data:
            currency_code = row['Family']
            if currency_code != 'USD1':
                continue
            currency_code = 'USD'
            selling_rate = float(row['SellingRates'].strip())
            buying_rate = float(row['BuyingRates'].strip())
            bank_id = 4

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
                session.execute(
                    text("""
                        INSERT INTO exchange_rates (date, base_currency_id, target_currency_id, selling_rate, buying_rate, bank_id)
                        VALUES (:date, :base_currency_id, :target_currency_id, :selling_rate, :buying_rate, :bank_id)
                    """),
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

def get_exchange_rates(api_key, date_str="06/01/2025", currency_type="2", language="th", timeout=10, max_retries=3):
    url = f"https://www.bangkokbank.com/api/exchangerateservice/Getfxrates/{date_str}/{currency_type}/{language}"

    headers = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9,th;q=0.8",
        "ocp-apim-subscription-key": api_key,
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
        "referer": "https://www.bangkokbank.com/th-th/personal/other-services/view-rates/foreign-exchange-rates",
    }
    retries = 0

    while retries < max_retries:
        try:
            start_time = time.time()
            response = requests.get(url, headers=headers, timeout=timeout)
            end_time = time.time()
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            retries += 1
            time.sleep(2)
        except requests.exceptions.RequestException as e:
            retries += 1
            time.sleep(2)
    return None

def process_exchange_rates():
    api_key = "7d1b09abe2ea413cbf95b2d99782ed37"
    start_period = get_start_period()

    if start_period != datetime.today().strftime('%Y-%m-%d'):
        start_date = datetime.strptime(start_period, '%Y-%m-%d')
        end_date = datetime.today()
        delta = timedelta(days=1)

        while start_date <= end_date:
            date_str = start_date.strftime('%d/%m/%Y')
            logger.info(f"Processing date: {date_str}")
            data = get_exchange_rates(api_key, date_str, currency_type="2", language="th", timeout=10, max_retries=3)
            if data:
                insert_exchange_rates(data, start_date.strftime('%Y-%m-%d'))
            else:
                logger.warning(f"No data fetched for {date_str}")
            start_date += delta
    else:
        date_str = datetime.today().strftime('%d/%m/%Y')
        logger.info(f"Processing date: {date_str}")
        data = get_exchange_rates(api_key, date_str, currency_type="2", language="th", timeout=10, max_retries=3)
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
    'bbl_exchange_rates',
    default_args=default_args,
    description='Fetch and insert BBL exchange rates daily',
    schedule_interval=timedelta(days=1),
    catchup=False,
)

task = PythonOperator(
    task_id='process_exchange_rates',
    python_callable=process_exchange_rates,
    dag=dag,
)
