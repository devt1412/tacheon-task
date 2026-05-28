"""
Task 2: Data Pipeline Engine (CoinGecko to BigQuery)
Author: Dev Tiwari
Description: Resilient, parameterized ETL pipeline fetching crypto market data,
             calculating custom risk metrics, and loading to a BigQuery Sandbox.
"""
import logging
import argparse
import requests
import time
from datetime import datetime
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuration Constants
API_BASE_URL = "https://api.coingecko.com/api/v3"
MARKETS_ENDPOINT = f"{API_BASE_URL}/coins/markets"

def fetch_market_data(vs_currency: str, limit: int, max_retries: int = 3, backoff_factor: int = 2):
    """Extract step: Calls public CoinGecko API with robust error handling and exponential backoff."""
    params = {
        "vs_currency": vs_currency.lower(),
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1,
        "sparkline": "false"
    }
    
    logging.info(f"Initiating HTTP GET request to {MARKETS_ENDPOINT}")
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(MARKETS_ENDPOINT, params=params, timeout=10)
            if response.status_code == 429:
                logging.warning(f"[Attempt {attempt}/{max_retries}] Rate limited by CoinGecko (HTTP 429).")
            elif response.status_code != 200:
                logging.error(f"[Attempt {attempt}/{max_retries}] API unexpected status code: {response.status_code}")
                response.raise_for_status()
            else:
                logging.info(f"Successfully extracted {len(response.json())} records from CoinGecko API.")
                return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"[Attempt {attempt}/{max_retries}] Network connection/protocol error: {str(e)}")
        
        if attempt < max_retries:
            sleep_time = backoff_factor ** attempt
            time.sleep(sleep_time)
            
    raise RuntimeError("Critical Pipeline Failure: Max API extraction retries exceeded.")

def transform_market_data(raw_data, base_currency: str):
    """Transform step: Handles missing values and adds sophisticated derived analytical metrics."""
    if not raw_data or not isinstance(raw_data, list):
        raise ValueError("Invalid payload structure provided to transformation matrix.")

    transformed_records = []
    ingestion_timestamp = datetime.utcnow().isoformat() + "Z"

    for record in raw_data:
        try:
            current_price = float(record.get("current_price") or 0.0)
            market_cap = float(record.get("market_cap") or 0.0)
            total_volume = float(record.get("total_volume") or 0.0)
            high_24h = record.get("high_24h")
            low_24h = record.get("low_24h")

            # Volatility Calculation
            if high_24h is not None and low_24h is not None and float(low_24h) > 0:
                volatility_spread = round(((float(high_24h) - float(low_24h)) / float(low_24h)) * 100, 4)
            else:
                volatility_spread = 0.0

            # Liquidity Calculation
            liquidity_ratio = round(total_volume / market_cap, 6) if market_cap > 0 else 0.0

            flattened_record = {
                "asset_id": str(record.get("id", "unknown_id")),
                "symbol": str(record.get("symbol", "unknown")).upper(),
                "name": str(record.get("name", "Unknown Name")),
                "base_currency": base_currency.upper(),
                "current_price": current_price,
                "market_cap": market_cap,
                "total_volume": total_volume,
                "high_24h": float(high_24h or 0.0),
                "low_24h": float(low_24h or 0.0),
                "intraday_volatility_spread_pct": volatility_spread,
                "liquidity_to_market_cap_ratio": liquidity_ratio,
                "extracted_at_utc": ingestion_timestamp
            }
            transformed_records.append(flattened_record)
        except Exception as record_error:
            logging.warning(f"Skipping record {record.get('id', 'Unknown')}: {str(record_error)}")
            continue

    return transformed_records

def load_to_bigquery(transformed_data, project_id: str, dataset_id: str, table_id: str):
    """
    Load step: Safely handles dataset verification, defines a strict table schema, 
    and streams batch ingestion into the target BigQuery Sandbox environment.
    """
    logging.info(f"Initializing BigQuery Client connection for target: {project_id}.{dataset_id}.{table_id}")
    client = bigquery.Client(project=project_id)

    # 1. Ensure the destination dataset exists
    dataset_ref = bigquery.DatasetReference(project_id, dataset_id)
    try:
        client.get_dataset(dataset_ref)
        logging.info(f"Dataset '{dataset_id}' successfully verified.")
    except Exception:
        logging.info(f"Dataset '{dataset_id}' not found. Creating a new one within Sandbox container...")
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        client.create_dataset(dataset, timeout=30)

    # 2. Define a production-grade schema with human-readable field metadata
    table_ref = dataset_ref.table(table_id)
    schema = [
        bigquery.SchemaField("asset_id", "STRING", mode="REQUIRED", description="Unique identifier for the asset"),
        bigquery.SchemaField("symbol", "STRING", mode="REQUIRED", description="Trading ticker symbol"),
        bigquery.SchemaField("name", "STRING", mode="NULLABLE", description="Full cryptocurrency asset name"),
        bigquery.SchemaField("base_currency", "STRING", mode="REQUIRED", description="Target fiat comparison base"),
        bigquery.SchemaField("current_price", "FLOAT", mode="NULLABLE", description="Last updated spot exchange rate price"),
        bigquery.SchemaField("market_cap", "FLOAT", mode="NULLABLE", description="Total circulating market capitalization"),
        bigquery.SchemaField("total_volume", "FLOAT", mode="NULLABLE", description="Aggregated 24-hour trading financial volume"),
        bigquery.SchemaField("high_24h", "FLOAT", mode="NULLABLE", description="Highest traded pricing match boundary over last 24h"),
        bigquery.SchemaField("low_24h", "FLOAT", mode="NULLABLE", description="Lowest traded pricing match boundary over last 24h"),
        bigquery.SchemaField("intraday_volatility_spread_pct", "FLOAT", mode="NULLABLE", description="Engineered Metric: Variance range percentage between 24h high/low"),
        bigquery.SchemaField("liquidity_to_market_cap_ratio", "FLOAT", mode="NULLABLE", description="Engineered Metric: Asset velocity metric (24h volume divided by market cap)"),
        bigquery.SchemaField("extracted_at_utc", "TIMESTAMP", mode="REQUIRED", description="UTC pipeline data extraction completion clock log")
    ]

    table = bigquery.Table(table_ref, schema=schema)
    
    # 3. Handle table verification/creation logic
    try:
        client.get_table(table_ref)
        logging.info(f"Target destination table '{table_id}' validated.")
    except Exception:
        logging.info(f"Target table '{table_id}' does not exist. Spawning standard template structure...")
        client.create_table(table, timeout=30)

    # 4. Stream data load job
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND, # Safely batches data increments
    )

    try:
        logging.info(f"Streaming data block batch ({len(transformed_data)} records) into BigQuery table...")
        load_job = client.load_table_from_json(transformed_data, table_ref, job_config=job_config)
        load_job.result() # Awaits asynchronous execution completion
        logging.info("Batch load ingestion job finalized successfully without schema violations.")
    except GoogleAPIError_as bq_err:
        logging.error(f"Ingestion Engine aborted mid-stream due to Cloud Exception: {str(bq_err)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CoinGecko Market Data Pipeline")
    parser.add_argument("--project_id", type=str, required=True, help="Your Google Cloud Platform Project ID")
    parser.add_argument("--dataset", type=str, default="crypto_analytics", help="Target BigQuery Dataset Name")
    parser.add_argument("--table", type=str, default="market_snapshots", help="Target BigQuery Table Name")
    parser.add_argument("--currency", type=str, default="usd", help="Target fiat currency (e.g., usd, inr)")
    parser.add_argument("--limit", type=int, default=50, help="Number of top assets to retrieve")
    
    args = parser.parse_args()
    logging.info("Pipeline triggered via CLI configuration arguments.")
    
    try:
        raw_payload = fetch_market_data(vs_currency=args.currency, limit=args.limit)
        transformed_payload = transform_market_data(raw_data=raw_payload, base_currency=args.currency)
        load_to_bigquery(
            transformed_data=transformed_payload,
            project_id=args.project_id,
            dataset_id=args.dataset,
            table_id=args.table
        )
    except Exception as pipeline_error:
        logging.critical(f"Pipeline execution halted prematurely: {str(pipeline_error)}")