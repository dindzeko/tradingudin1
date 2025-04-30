import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import time

# Fungsi untuk membaca data dari Google Drive (file Excel)
def load_google_drive_excel(file_url):
    try:
        file_id = file_url.split("/d/")[1].split("/")[0]
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        df = pd.read_excel(download_url, engine='openpyxl')

        if 'Ticker' not in df.columns:
            st.error("The 'Ticker' column is missing in the Excel file.")
            return None

        st.success("Successfully loaded data from Google Drive!")
        st.info(f"Number of rows read: {len(df)}")
        st.info(f"Columns in the Excel file: {', '.join(df.columns)}")

        return df[['Ticker']].dropna().drop_duplicates()
    except Exception as e:
        st.error(f"Error loading Excel file from Google Drive: {e}")
        return None


# Fungsi untuk mengambil data saham dengan batch download (lebih stabil)
@st.cache_data(ttl=3600)  # Cache selama 1 jam
def fetch_batch_stock_data(tickers, end_date):
    tickers_jk = [f"{t}.JK" for t in tickers]  # Tambahkan .JK ke semua ticker
    start_date = end_date - timedelta(days=30)

    st.write("Fetching data for tickers with .JK:")
    
    try:
        data = yf.download(
            tickers=" ".join(tickers_jk),
            start=start_date,
            end=end_date,
            group_by="ticker",
            auto_adjust=True,
            threads=True
        )
        return data
    except Exception as e:
        st.error(f"Error fetching batch data: {str(e)}")
        return None


# Fungsi untuk mendeteksi pola bearish 4 candle
def detect_pattern(data):
    if len(data) >= 4:
        data = data.tail(4)
        open_prices = data['Open'].values
        close_prices = data['Close'].values

        # Candle 1: Bullish panjang
        bull_candle_1 = close_prices[0] > open_prices[0] and (close_prices[0] - open_prices[0]) > 0.02 * open_prices[0]

        # Candle 2: Bearish dan lebih rendah dari candle 1
        bear_candle_2 = close_prices[1] < open_prices[1]
        lower_close_2 = close_prices[1] < close_prices[0]

        # Candle 3: Bearish turun lagi
        bear_candle_3 = close_prices[2] < open_prices[2]
        lower_close_3 = close_prices[2] < close_prices[1]

        # Candle 4: Bearish terus
        bear_candle_4 = close_prices[3] < open_prices[3]
        lower_close_4 = close_prices[3] < close_prices[2]

        uptrend_start = close_prices[3] > close_prices[0]

        return (
            bull_candle_1 and
            bear_candle_2 and lower_close_2 and
            bear_candle_3 and lower_close_3 and
            bear_candle_4 and lower_close_4 and
            uptrend_start
        )
    return False


# Main function
def main():
    st.title("Stock Screening - Pola 4 Candle Bearish (Indonesia)")

    # URL file Excel di Google Drive
    file_url = "https://docs.google.com/spreadsheets/d/1t6wgBIcPEUWMq40GdIH1GtZ8dvI9PZ2v/edit?usp=drive_link&ouid=106044501644618784207&rtpof=true&sd=true"

    # Load data dari Google Drive
    st.info("Loading data from Google Drive...")
    df = load_google_drive_excel(file_url)
    if df is None or 'Ticker' not in df.columns:
        st.error("Failed to load data or 'Ticker' column is missing.")
        return

    tickers = df['Ticker'].astype(str).str.strip().str.upper().unique()
    total_tickers = len(tickers)

    # Date input
    analysis_date = st.date_input("Analysis Date", value=datetime.today())

    # Analyze button
    if st.button("Analyze Stocks"):
        results = []
        bbc_data = None

        # Konversi ticker menjadi format .JK
        tickers_jk = [f"{t}.JK" for t in tickers]

        # Ambil semua data sekaligus
        stock_data = fetch_batch_stock_data(tickers, analysis_date)

        if stock_data is None:
            st.error("No data retrieved for any ticker.")
            return

        progress_bar = st.progress(0)
        progress_text = st.empty()

        for i, ticker in enumerate(tickers):
            full_ticker = f"{ticker}.JK"

            # Cek apakah data tersedia
            if full_ticker in stock_data.columns.get_level_values(0):
                data = stock_data[full_ticker].dropna()
                if len(data) >= 4:
                    if detect_pattern(data):
                        latest_close = data['Close'][-1]
                        results.append({
                            "Ticker": ticker,
                            "Last Close": round(latest_close, 2),
                            "Pattern Detected": "Unconfirmed Mathold"
                        })

                    # Simpan data BBCA jika ada
                    if ticker == "BBCA":
                        bbc_data = data.tail(4)

            # Update progress bar
            progress = (i + 1) / total_tickers
            progress_bar.progress(progress)
            progress_text.text(f"Progress: {int(progress * 100)}%")

        # Tampilkan hasil akhir
        if results:
            st.subheader("✅ Saham yang Memenuhi Pola")
            results_df = pd.DataFrame(results)
            st.dataframe(results_df)
        else:
            st.info("❌ Tidak ada saham yang memenuhi pola.")

        # Tampilkan data BBCA khusus
        st.markdown("---")
        st.subheader("🔍 Data BBCA.JK (Jika Tersedia)")
        if bbc_data is not None and not bbc_data.empty:
            st.dataframe(bbc_data[['Open', 'High', 'Low', 'Close', 'Volume']])
        else:
            st.warning("Tidak ada data ditemukan untuk BBCA.JK atau tidak memenuhi pola.")

if __name__ == "__main__":
    main()
