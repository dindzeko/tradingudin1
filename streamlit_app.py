import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

# Fungsi membaca Excel dari Google Drive
def load_google_drive_excel(file_url):
    try:
        file_id = file_url.split("/d/")[1].split("/")[0]
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        df = pd.read_excel(download_url, engine='openpyxl')

        if 'Ticker' not in df.columns:
            st.error("Kolom 'Ticker' tidak ditemukan di file Excel.")
            return None

        st.success("✅ Berhasil memuat data dari Google Drive!")
        st.info(f"Jumlah baris: {len(df)}")
        return df

    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
        return None

# Fungsi mengambil data harga saham
def get_stock_data(ticker, end_date):
    try:
        stock = yf.Ticker(f"{ticker}.JK")
        start_date = end_date - timedelta(days=60)
        data = stock.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))

        return data if not data.empty else None
    except Exception as e:
        st.error(f"Gagal mengambil data untuk {ticker}: {e}")
        return None

# Fungsi mendeteksi pola 4 candle
def detect_pattern(data):
    recent = data.tail(4)
    if len(recent) < 4:
        return False

    c1, c2, c3, c4 = recent.iloc[0:4]

    is_c1_bullish = c1['Close'] > c1['Open'] and (c1['Close'] - c1['Open']) > 0.02 * c1['Open']
    is_c2_bearish = c2['Close'] < c2['Open'] and c2['Close'] < c1['Close']
    is_c3_bearish = c3['Close'] < c3['Open']
    is_c4_bearish = c4['Close'] < c4['Open']
    is_uptrend = c4['Close'] < c1['Close']
    is_close_sequence = c2['Close'] > c3['Close'] > c4['Close']

    return all([is_c1_bullish, is_c2_bearish, is_c3_bearish, is_c4_bearish, is_uptrend, is_close_sequence])

# Fungsi menghitung indikator tambahan
def calculate_additional_metrics(data):
    df = data.copy()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['RSI'] = compute_rsi(df['Close'], 14)
    last_row = df.iloc[-1]

    return {
        "MA20": round(last_row['MA20'], 2) if not np.isnan(last_row['MA20']) else None,
        "RSI": round(last_row['RSI'], 2) if not np.isnan(last_row['RSI']) else None,
        "Volume": int(last_row['Volume']) if not np.isnan(last_row['Volume']) else None
    }

# Fungsi RSI
def compute_rsi(close_series, period=14):
    delta = close_series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=period).mean()
    avg_loss = pd.Series(loss).rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Main App
def main():
    st.title("📊 Stock Screener - Pola 4 Candle + Analisis MA20, RSI & Volume")

    file_url = "https://docs.google.com/spreadsheets/d/1t6wgBIcPEUWMq40GdIH1GtZ8dvI9PZ2v/edit?usp=drive_link"
    df = load_google_drive_excel(file_url)

    if df is None or 'Ticker' not in df.columns:
        return

    tickers = df['Ticker'].dropna().unique().tolist()
    analysis_date = st.date_input("Tanggal Analisis", value=datetime.today())

    if st.button("🔍 Mulai Screening"):
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
                        "Pattern": "Unconfirmed Mathold",
                        "MA20": metrics["MA20"],
                        "RSI": metrics["RSI"],
                        "Volume": metrics["Volume"]
                    })

            progress = (i + 1) / len(tickers)
            progress_bar.progress(progress)
            progress_text.text(f"Progress: {int(progress * 100)}%")

        if results:
            st.subheader("✅ Saham yang Memenuhi Pola & Indikator Tambahan")
            st.dataframe(pd.DataFrame(results))
        else:
            st.warning("Tidak ada saham yang cocok dengan pola.")

if __name__ == "__main__":
    main()
