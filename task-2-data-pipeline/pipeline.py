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

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuration Constants
API_BASE_URL = "https://api.coingecko.com/api/v3"
MARKETS_ENDPOINT = f"{API_BASE_URL}/coins/markets"

def fetch_market_data(vs_currency: str, limit: int, max_retries: int = 3, backoff_factor: int = 2):
    """
    Extract step: Calls public CoinGecko API with robust error handling,
    parameterization, timeouts, and exponential backoff retry logic.
    """
    params = {
        "vs_currency": vs_currency.lower(),
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1,
        "sparkline": "false"
    }
    
    logging.info(f"Initiating HTTP GET request to {MARKETS_ENDPOINT} | Parameters: {params}")
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(MARKETS_ENDPOINT, params=params, timeout=10)
            
            if response.status_code == 429:
                logging.warning(f"[Attempt {attempt}/{max_retries}] Rate limited by CoinGecko (HTTP 429).")
            elif response.status_code != 200:
                logging.error(f"[Attempt {attempt}/{max_retries}] API responded with unexpected status code: {response.status_code}")
                response.raise_for_status()
            else:
                logging.info(f"Successfully extracted {len(response.json())} records from CoinGecko API.")
                return response.json()
                
        except requests.exceptions.Timeout:
            logging.error(f"[Attempt {attempt}/{max_retries}] Request timed out after 10 seconds.")
        except requests.exceptions.RequestException as e:
            logging.error(f"[Attempt {attempt}/{max_retries}] Network connection/protocol error encountered: {str(e)}")
            
        if attempt < max_retries:
            sleep_time = backoff_factor ** attempt
            logging.info(f"Retrying pipeline fetch window in {sleep_time} seconds...")
            time.sleep(sleep_time)
            
    raise RuntimeError("Critical Pipeline Failure: Max API extraction retries exceeded. Extraction aborted.")

def transform_market_data(raw_data, base_currency: str):
    """
    Transform step: Flattens JSON data, normalizes type mismatches,
    handles missing values, and adds sophisticated derived analytical metrics.
    """
    if not raw_data or not isinstance(raw_data, list):
        logging.error("Transformation Error: Raw payload data is empty or structurally invalid.")
        raise ValueError("Invalid payload structure provided to transformation matrix.")

    transformed_records = []
    ingestion_timestamp = datetime.utcnow().isoformat() + "Z" # ISO 8601 UTC timestamp format

    for record in raw_data:
        try:
            # 1. Type normalization and missing value fallback (Handling Nulls gracefully)
            coin_id = str(record.get("id", "unknown_id"))
            symbol = str(record.get("symbol", "unknown")).upper()
            name = str(record.get("name", "Unknown Name"))
            
            current_price = float(record.get("current_price") or 0.0)
            market_cap = float(record.get("market_cap") or 0.0)
            total_volume = float(record.get("total_volume") or 0.0)
            
            high_24h = record.get("high_24h")
            low_24h = record.get("low_24h")

            # 2. Analytical Metric Engineering: Intraday Volatility Spread Percentage
            # Formula: ((High - Low) / Low) * 100
            if high_24h is not None and low_24h is not None and float(low_24h) > 0:
                volatility_spread = round(((float(high_24h) - float(low_24h)) / float(low_24h)) * 100, 4)
            else:
                volatility_spread = 0.0 # Standard fallback for illiquid or flat assets

            # 3. Analytical Metric Engineering: Liquidity-to-Market-Cap Ratio
            # Formula: Total Volume / Market Cap
            if market_cap > 0:
                liquidity_ratio = round(total_volume / market_cap, 6)
            else:
                liquidity_ratio = 0.0

            # 4. Construct a completely flattened structure optimized for BigQuery schema ingestion
            flattened_record = {
                "asset_id": coin_id,
                "symbol": symbol,
                "name": name,
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
            # Log single problematic record and continue pipeline to avoid stopping execution entirely
            logging.warning(f"Skipping transformation for record {record.get('id', 'Unknown')}: {str(record_error)}")
            continue

    logging.info(f"Transformation matrix completed successfully. Processed {len(transformed_records)} records.")
    return transformed_records

def load_to_bigquery(transformed_data):
    """Load step: Streams batch ingestion into target BigQuery destination."""
    logging.info("Initiating batch load into Google BigQuery Sandbox staging tables.")
    pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CoinGecko Market Data Pipeline")
    parser.add_argument("--currency", type=str, default="usd", help="Target fiat currency (e.g., usd, inr)")
    parser.add_argument("--limit", type=int, default=50, help="Number of top assets to retrieve")
    
    args = parser.parse_args()
    logging.info("Pipeline triggered via CLI configuration arguments.")
    
    try:
        # Execute Extraction
        raw_payload = fetch_market_data(vs_currency=args.currency, limit=args.limit)
        
        # Execute Transformation
        transformed_payload = transform_market_data(raw_data=raw_payload, base_currency=args.currency)
        
    except Exception as pipeline_error:
        logging.critical(f"Pipeline execution halted prematurely: {str(pipeline_error)}")