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

        if 'Ticker' not in df.columns or 'Papan Pencatatan' not in df.columns:
            st.error("Kolom 'Ticker' dan 'Papan Pencatatan' harus ada di file Excel.")
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

# Fungsi deteksi pola 4 candle
def detect_pattern(data):
    recent = data.tail(4)
    if recent.shape[0] != 4:
        return False

    c1, c2, c3, c4 = recent.iloc[0], recent.iloc[1], recent.iloc[2], recent.iloc[3]

    is_c1_bullish = c1['Close'] > c1['Open'] and (c1['Close'] - c1['Open']) > 0.02 * c1['Open']
    is_c2_bearish = c2['Close'] < c2['Open'] and c2['Close'] < c1['Close']
    is_c3_bearish = c3['Close'] < c3['Open']
    is_c4_bearish = c4['Close'] < c4['Open']
    is_uptrend = c4['Close'] < c1['Close']
    is_close_sequence = c2['Close'] > c3['Close'] > c4['Close']

    return all([
        is_c1_bullish,
        is_c2_bearish,
        is_c3_bearish,
        is_c4_bearish,
        is_uptrend,
        is_close_sequence
    ])

# Fungsi RSI
def compute_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Fungsi OBV
def compute_obv(df):
    obv = [0]
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['Close'].iloc[i - 1]:
            obv.append(obv[-1] + df['Volume'].iloc[i])
        elif df['Close'].iloc[i] < df['Close'].iloc[i - 1]:
            obv.append(obv[-1] - df['Volume'].iloc[i])
        else:
            obv.append(obv[-1])
    df['OBV'] = obv
    return df

# Interpretasi OBV
def interpret_obv(df):
    if df['OBV'].iloc[-1] > df['OBV'].iloc[-2]:
        return "Tekanan Beli"
    elif df['OBV'].iloc[-1] < df['OBV'].iloc[-2]:
        return "Tekanan Jual"
    else:
        return "Netral"

# Fungsi menghitung metrik tambahan
def calculate_additional_metrics(data):
    df = data.copy()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['RSI'] = compute_rsi(df['Close'], 14)
    df = compute_obv(df)
    obv_sentiment = interpret_obv(df)

    last_20 = df.tail(20)
    high = last_20['High'].max()
    low = last_20['Low'].min()
    fib_levels = {
        'Fib_0.0': round(high, 2),
        'Fib_0.236': round(high - 0.236 * (high - low), 2),
        'Fib_0.382': round(high - 0.382 * (high - low), 2),
        'Fib_0.5': round((high + low) / 2, 2),
        'Fib_0.618': round(high - 0.618 * (high - low), 2),
        'Fib_1.0': round(low, 2)
    }

    bins = np.linspace(low, high, 20)
    df['Price_bin'] = pd.cut(df['Close'], bins)
    volume_profile = df.groupby('Price_bin')['Volume'].sum()
    most_volume_bin = volume_profile.idxmax()
    volume_support_resist = round((most_volume_bin.left + most_volume_bin.right) / 2, 2)

    last_row = df.iloc[-1]

    return {
        "MA20": round(last_row['MA20'], 2) if not np.isnan(last_row['MA20']) else None,
        "RSI": round(last_row['RSI'], 2) if not np.isnan(last_row['RSI']) else None,
        "Volume": int(last_row['Volume']) if not np.isnan(last_row['Volume']) else None,
        "Fibonacci_Levels": fib_levels,
        "Volume_Profile_Level": volume_support_resist,
        "OBV_Sentiment": obv_sentiment
    }

# Main App
def main():
    st.title("📊 Stock Screener - Unconfirmed MatHold")

    file_url = "https://docs.google.com/spreadsheets/d/1t6wgBIcPEUWMq40GdIH1GtZ8dvI9PZ2v/edit?usp=drive_link"
    df = load_google_drive_excel(file_url)

    if df is None or 'Ticker' not in df.columns:
        return

    tickers = df['Ticker'].dropna().unique().tolist()
    analysis_date = st.date_input("📅 Tanggal Analisis", value=datetime.today())

    if st.button("🔍 Mulai Screening"):
        results = []
        progress_bar = st.progress(0)
        progress_text = st.empty()

        for i, ticker in enumerate(tickers):
            data = get_stock_data(ticker, analysis_date)

            if data is not None and len(data) >= 20:
                if detect_pattern(data):
                    metrics = calculate_additional_metrics(data)
                    papan = df[df['Ticker'] == ticker]['Papan Pencatatan'].values[0]

                    results.append({
                        "Ticker": ticker,
                        "Papan": papan,
                        "Last Close": round(data['Close'].iloc[-1], 2),
                        "MA20": metrics["MA20"],
                        "RSI": metrics["RSI"],
                        "OBV": metrics["OBV_Sentiment"],
                        "Volume": metrics["Volume"],
                        "Volume Profile": metrics["Volume_Profile_Level"],
                        "Fib 0.382": metrics["Fibonacci_Levels"]['Fib_0.382'],
                        "Fib 0.5": metrics["Fibonacci_Levels"]['Fib_0.5'],
                        "Fib 0.618": metrics["Fibonacci_Levels"]['Fib_0.618'],
                    })

            progress = (i + 1) / len(tickers)
            progress_bar.progress(progress)
            progress_text.text(f"Progress: {int(progress * 100)}%")

        if results:
            st.subheader("✅ Saham yang Memenuhi Kriteria")
            st.dataframe(pd.DataFrame(results))
        else:
            st.warning("Tidak ada saham yang cocok dengan pola.")

if __name__ == "__main__":
    main()
