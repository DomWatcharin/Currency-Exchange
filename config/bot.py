import http.client
import gzip
from io import BytesIO
from datetime import datetime, timedelta
import pandas as pd
import json
import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add the parent directory to the sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from app.core.config import settings

# Ensure the DATABASE_URL is correctly set
DATABASE_URL = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
logging.info(f"Connecting to database at {DATABASE_URL}")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
                logging.info(f"Successfully inserted exchange rates for {row['date']}")
            else:
                logging.info(f"Exchange rates for {row['date']} already exist")
    except Exception as e:
        session.rollback()
        logging.error(f"Error inserting data: {e}")
    finally:
        session.close()

end_period = datetime.today().strftime('%Y-%m-%d')
start_period = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
currency = "USD"

exchange_rate_data = fetch_daily_avg_exg_rate(start_period, end_period, currency)
df = json_to_dataframe(exchange_rate_data)

df = df.sort_values(by='date').reset_index(drop=True)

insert_exchange_rates(df)