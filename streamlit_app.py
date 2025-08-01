import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

# =======================
# Fungsi Utilitas
# =======================

def load_google_drive_excel(file_url):
    try:
        file_id = file_url.split("/d/")[1].split("/")[0]
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        df = pd.read_excel(download_url, engine='openpyxl')

        if 'Ticker' not in df.columns or 'Papan Pencatatan' not in df.columns:
            st.error("Kolom 'Ticker' atau 'Papan Pencatatan' tidak ditemukan di file.")
            return None

        st.success("✅ Berhasil memuat data dari Google Drive!")
        st.info(f"Jumlah baris: {len(df)}")
        return df

    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
        return None

def get_stock_data(ticker, end_date):
    try:
        stock = yf.Ticker(f"{ticker}.JK")
        start_date = end_date - timedelta(days=60)
        data = stock.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        return data if not data.empty else None
    except Exception as e:
        st.error(f"Gagal mengambil data untuk {ticker}: {e}")
        return None

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

    return all([is_c1_bullish, is_c2_bearish, is_c3_bearish, is_c4_bearish, is_uptrend, is_close_sequence])

# =======================
# Indikator Tambahan
# =======================

def compute_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_obv(data):
    obv = [0]
    for i in range(1, len(data)):
        if data['Close'].iloc[i] > data['Close'].iloc[i - 1]:
            obv.append(obv[-1] + data['Volume'].iloc[i])
        elif data['Close'].iloc[i] < data['Close'].iloc[i - 1]:
            obv.append(obv[-1] - data['Volume'].iloc[i])
        else:
            obv.append(obv[-1])
    return pd.Series(obv, index=data.index)

def compute_mfi(data, period=14):
    typical_price = (data['High'] + data['Low'] + data['Close']) / 3
    money_flow = typical_price * data['Volume']
    positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
    negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
    pos_mf = positive_flow.rolling(window=period).sum()
    neg_mf = negative_flow.rolling(window=period).sum()
    mfi = 100 - (100 / (1 + (pos_mf / neg_mf)))
    return mfi

def calculate_additional_metrics(data):
    df = data.copy()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['RSI'] = compute_rsi(df['Close'])
    df['OBV'] = compute_obv(df)
    df['MFI'] = compute_mfi(df)

    last = df.iloc[-1]

    sentiment = "Neutral"
    if last['RSI'] < 30 and last['MFI'] < 20 and df['OBV'].iloc[-1] > df['OBV'].iloc[-2]:
        sentiment = "Bullish"
    elif last['RSI'] > 70 and last['MFI'] > 80 and df['OBV'].iloc[-1] < df['OBV'].iloc[-2]:
        sentiment = "Bearish"

    return {
        "MA20": round(last['MA20'], 2) if not np.isnan(last['MA20']) else None,
        "RSI": round(last['RSI'], 2) if not np.isnan(last['RSI']) else None,
        "MFI": round(last['MFI'], 2) if not np.isnan(last['MFI']) else None,
        "OBV": int(last['OBV']),
        "Volume": int(last['Volume']),
        "Sentiment": sentiment
    }

# =======================
# Main App
# =======================

def main():
    st.title("📊 Stock Screener - Pola 4 Candle + Analisis Sentimen")

    file_url = "https://docs.google.com/spreadsheets/d/1t6wgBIcPEUWMq40GdIH1GtZ8dvI9PZ2v/edit?usp=drive_link"
    df_excel = load_google_drive_excel(file_url)

    if df_excel is None:
        return

    tickers = df_excel['Ticker'].dropna().unique().tolist()
    papan_dict = dict(zip(df_excel['Ticker'], df_excel['Papan Pencatatan']))

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
                        "Papan Pencatatan": papan_dict.get(ticker, "-"),
                        "Last Close": round(data['Close'].iloc[-1], 2),
                        "MA20": metrics["MA20"],
                        "RSI": metrics["RSI"],
                        "MFI": metrics["MFI"],
                        "OBV": metrics["OBV"],
                        "Volume": metrics["Volume"],
                        "Sentimen": metrics["Sentiment"]
                    })

            progress = (i + 1) / len(tickers)
            progress_bar.progress(progress)
            progress_text.text(f"Progress: {int(progress * 100)}%")

        if results:
            st.subheader("✅ Hasil Screening & Analisa")
            st.dataframe(pd.DataFrame(results))
        else:
            st.warning("Tidak ada saham yang memenuhi kriteria pola.")

if __name__ == "__main__":
    main()
