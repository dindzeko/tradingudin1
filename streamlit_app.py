import yfinance as yf
from datetime import datetime, timedelta
import time
import pandas as pd

# Fungsi utama: ambil data 4 hari terakhir dari Yahoo Finance
def get_last_4_days_data(ticker, delay=0.5):
    print(f"Fetching data for {ticker}...")
    time.sleep(delay)  # Hindari rate limit

    try:
        stock = yf.Ticker(ticker)
        end_date = datetime.today()
        start_date = end_date - timedelta(days=7)  # Ambil 7 hari agar pasti ada 4 hari perdagangan

        df = stock.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))

        if df.empty:
            print(f"No data found for {ticker}")
            return None

        # Hanya ambil 4 baris terakhir jika cukup datanya
        latest_data = df.tail(4).copy()
        latest_data.reset_index(inplace=True)
        latest_data['Ticker'] = ticker

        print(f"Success retrieving data for {ticker}")
        return latest_data[['Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Volume']]
    
    except Exception as e:
        print(f"Error fetching data for {ticker}: {str(e)}")
        return None


# Contoh daftar ticker BEI (boleh ganti sesuai kebutuhan)
tickers_to_fetch = [
    'BBCA', 'BBRI', 'TLKM', 'UNVR',
    'ASII.JK', 'BMRI.JK', 'ADRO.JK', 'INDF.JK',
    'ICBP.JK', 'INCO.JK', 'PGAS.JK', 'KLBF.JK'
]

# Looping untuk mengambil data semua ticker
all_data = []

for ticker in tickers_to_fetch:
    result = get_last_4_days_data(ticker, delay=1)  # Delay 1 detik per ticker
    if result is not None:
        all_data.append(result)

# Gabungkan semua data
if all_data:
    final_df = pd.concat(all_data, ignore_index=True)
    
    # Tampilkan di layar
    print("\n📊 Final Data (Last 4 Trading Days):")
    print(final_df.to_string(index=False))
    
    # Simpan ke file CSV (opsional)
    output_file = "last_4_days_stock_data.csv"
    final_df.to_csv(output_file, index=False)
    print(f"\n💾 Data saved to '{output_file}'")
else:
    print("No data retrieved for any ticker.")
