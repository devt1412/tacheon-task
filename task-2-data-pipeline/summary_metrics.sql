-- summary_metrics.sql
-- Description: Top 5 Highest Volatility Assets with High Liquidity Velocity
-- Purpose: Filters out dead tokens and isolates high-priority market swings for market analysts.

WITH structured_snapshots AS (
    SELECT 
        symbol,
        name,
        current_price,
        intraday_volatility_spread_pct,
        liquidity_to_market_cap_ratio,
        extracted_at_utc,
        ROW_NUMBER() OVER(PARTITION BY symbol ORDER BY extracted_at_utc DESC) as latest_row
    FROM 
        `crypto_analytics.market_snapshots`
)
SELECT 
    symbol,
    name,
    current_price,
    intraday_volatility_spread_pct,
    liquidity_to_market_cap_ratio
FROM 
    structured_snapshots
WHERE 
    latest_row = 1 
    AND liquidity_to_market_cap_ratio > 0.01 -- Filter out illiquid low-velocity assets
ORDER BY 
    intraday_volatility_spread_pct DESC
LIMIT 5;