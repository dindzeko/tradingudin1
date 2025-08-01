import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

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
        return df

    except Exception as e:
        st.error(f"Error loading Excel file: {e}")
        return None

# Fungsi untuk mengambil data saham
def get_stock_data(ticker, end_date):
    try:
        stock = yf.Ticker(f"{ticker}.JK")
        start_date = end_date - timedelta(days=60)  # Ambil lebih banyak data untuk MA & RSI
        data = stock.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))

        return data if not data.empty else None
    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {str(e)}")
        return None

# Deteksi pola 4 candle
def detect_pattern(data):
    if len(data) >= 4:
        recent = data.tail(4)
        c1, c2, c3, c4 = recent.iloc[0:4]

        is_c1_bullish = c1['Close'] > c1['Open'] and (c1['Close'] - c1['Open']) > 0.02 * c1['Open']
        is_c2_bearish = c2['Close'] < c2['Open'] and c2['Close'] < c1['Close']
        is_c3_bearish = c3['Close'] < c3['Open']
        is_c4_bearish = c4['Close'] < c4['Open']
        is_uptrend = c4['Close'] < c1['Close']
        is_close_sequence = c2['Close'] > c3['Close'] > c4['Close']

        return all([is_c1_bullish, is_c2_bearish, is_c3_bearish, is_c4_bearish, is_uptrend, is_close_sequence])
    return False

# Fungsi untuk menghitung indikator tambahan
def calculate_additional_metrics(data):
    df = data.copy()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['RSI'] = compute_rsi(df['Close'], 14)
    last_row = df.iloc[-1]
    return {
        "MA20": round(last_row['MA20'], 2),
        "RSI": round(last_row['RSI'], 2),
        "Volume": int(last_row['Volume'])
    }

# Fungsi untuk menghitung RSI
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=period).mean()
    avg_loss = pd.Series(loss).rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Main App
def main():
    st.title("Stock Screening - 4 Candle + Technical Analysis")

    file_url = "https://docs.google.com/spreadsheets/d/1t6wgBIcPEUWMq40GdIH1GtZ8dvI9PZ2v/edit?usp=drive_link"
    df = load_google_drive_excel(file_url)
    if df is None or 'Ticker' not in df.columns:
        return

    tickers = df['Ticker'].tolist()
    analysis_date = st.date_input("Analysis Date", value=datetime.today())

    if st.button("Analyze Stocks"):
        results = []
        progress_bar = st.progress(0)
        progress_text = st.empty()

        for i, ticker in enumerate(tickers):
            data = get_stock_data(ticker, analysis_date)
            if data is not None and len(data) >= 20:
                if detect_pattern(data):
                    metrics = calculate_additional_metrics(data)
                    results.append({
                        "Ticker": ticker,
                        "Last Close": round(data['Close'].iloc[-1], 2),
                        "Pattern Detected": "Unconfirmed Mathold",
                        "MA20": metrics["MA20"],
                        "RSI": metrics["RSI"],
                        "Volume": metrics["Volume"]
                    })
            progress = (i + 1) / len(tickers)
            progress_bar.progress(progress)
            progress_text.text(f"Progress: {int(progress * 100)}%")

        if results:
            st.subheader("📈 Result: Stocks Matching Pattern + Technicals")
            st.dataframe(pd.DataFrame(results))
        else:
            st.warning("No stocks match the pattern.")

if __name__ == "__main__":
    main()
