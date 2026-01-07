"""
Quick test to verify yfinance works for Korean stocks
"""
import yfinance as yf
import pandas as pd

# Test Samsung Electronics (005930)
print("Testing Yahoo Finance for Korean stocks...")
print("Testing Samsung Electronics (005930.KS)...")

try:
    ticker = "005930.KS"
    data = yf.download(ticker, start="2024-01-01", end="2024-12-31", progress=False)

    if not data.empty:
        print(f"✅ Success: Downloaded {len(data)} days of data for Samsung")
        print(f"Date range: {data.index[0].date()} to {data.index[-1].date()}")
        print(f"Columns: {list(data.columns)}")
        print(f"Sample close prices: {data['Close'].head().values}")
    else:
        print("❌ No data returned")

except Exception as e:
    print(f"❌ Error: {e}")

# Test 2025 data availability
print("\nTesting 2025 data availability...")
try:
    ticker = "005930.KS"
    data_2025 = yf.download(ticker, start="2025-01-01", end="2025-01-31", progress=False)

    if not data_2025.empty:
        print(f"✅ 2025 data available: {len(data_2025)} days")
        print(f"Latest date: {data_2025.index[-1].date()}")
    else:
        print("⚠️ No 2025 data available yet")

except Exception as e:
    print(f"❌ Error fetching 2025 data: {e}")

print("Test complete.")