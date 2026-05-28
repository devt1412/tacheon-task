# Task 2: Parameterized Crypto Market Data Pipeline

## 1. Architectural Overview & API Selection
This pipeline utilizes the public **CoinGecko API** (`/coins/markets` endpoint) to extract real-time spot pricing, transaction velocity, and capitalization metrics for top-tier digital assets.

### Why CoinGecko?
* Provides clean, highly relational, structured JSON schemas out of the box.
* Offers a fair public tier without early authentication friction, letting us focus entirely on building data pipeline resiliency.
* Delivers multiple volatile financial vectors (24h highs, lows, and volumes), providing excellent raw material for downstream custom metric engineering.

---

## 2. Engineered Data Transformation & Calculations
Raw API streams are rarely ready for analytical consumption. The pipeline standardizes structural data types, maps null fallbacks, and calculates two custom metrics:

1. **Intraday Volatility Spread Percentage (`intraday_volatility_spread_pct`)**

$$
\text{Volatility Spread \%} = \left( \frac{\text{24h High} - \text{24h Low}}{\text{24h Low}} \right) \times 100
$$

*Analytical Value:* Instantly flags assets experiencing massive trading price swings, helping marketing analysts identify high-momentum assets for ad campaign targeting.
   
2. **Liquidity-to-Market-Cap Ratio (`liquidity_to_market_cap_ratio`)**

$$
\text{Liquidity Ratio} = \frac{\text{Total 24h Volume}}{\text{Total Market Capitalization}}
$$

*Analytical Value:* Measures asset velocity. It helps analysts separate true liquid market trends from low-volume, illiquid price spikes.

---

## 3. Local Installation & Execution Guide

### Prerequisites
Ensure you have Python 3.8+ installed along with the official Google Cloud BigQuery client library:
```bash
pip install requests google-cloud-bigquery
```

### Execution Parameters

The pipeline is fully parameterized via CLI arguments, eliminating hardcoded variables:  
* `--project_id` (Required): Your target GCP Project identifier.  
* `--currency` (Optional, Default: usd): Target fiat currency baseline (e.g., usd, inr).  
* `--limit` (Optional, Default: 50): Maximum records to ingest per batch.  

### Running the Pipeline

```bash
python pipeline.py --project_id "your-gcp-project-id" --currency "usd" --limit 25
