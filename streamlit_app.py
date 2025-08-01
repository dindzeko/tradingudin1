import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

# === Fungsi Load File Excel dari Google Drive ===
def load_google_drive_excel(file_url):
    try:
        file_id = file_url.split("/d/")[1].split("/")[0]
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        df = pd.read_excel(download_url, engine='openpyxl')

        if 'Ticker' not in df.columns or 'Papan Pencatatan' not in df.columns:
            st.error("Kolom 'Ticker' atau 'Papan Pencatatan' tidak ditemukan di file Excel.")
            return None

        st.success("✅ Berhasil memuat data dari Google Drive!")
        return df

    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
        return None

# === Fungsi Ambil Data Saham ===
def get_stock_data(ticker, end_date):
    try:
        stock = yf.Ticker(f"{ticker}.JK")
        start_date = end_date - timedelta(days=90)
        data = stock.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        return data if not data.empty else None
    except:
        return None

# === Deteksi Pola 4 Candle ===
def detect_pattern(data):
    recent = data.tail(4)
    if recent.shape[0] != 4:
        return False
    c1, c2, c3, c4 = recent.iloc[0], recent.iloc[1], recent.iloc[2], recent.iloc[3]
    return all([
        c1['Close'] > c1['Open'] and (c1['Close'] - c1['Open']) > 0.02 * c1['Open'],
        c2['Close'] < c2['Open'] and c2['Close'] < c1['Close'],
        c3['Close'] < c3['Open'],
        c4['Close'] < c4['Open'],
        c4['Close'] < c1['Close'],
        c2['Close'] > c3['Close'] > c4['Close']
    ])

# === RSI ===
def compute_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# === OBV ===
def compute_obv(df):
    obv = [0]
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['Close'].iloc[i - 1]:
            obv.append(obv[-1] + df['Volume'].iloc[i])
        elif df['Close'].iloc[i] < df['Close'].iloc[i - 1]:
            obv.append(obv[-1] - df['Volume'].iloc[i])
        else:
            obv.append(obv[-1])
    return pd.Series(obv, index=df.index)

# === MFI ===
def compute_mfi(df, period=14):
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    money_flow = typical_price * df['Volume']
    pos_flow = money_flow.where(typical_price > typical_price.shift(), 0)
    neg_flow = money_flow.where(typical_price < typical_price.shift(), 0)
    pos_mf = pos_flow.rolling(window=period).sum()
    neg_mf = neg_flow.rolling(window=period).sum()
    mfi = 100 - (100 / (1 + pos_mf / neg_mf))
    return mfi

# === Hitung Semua Indikator Tambahan ===
def calculate_metrics(data):
    df = data.copy()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['RSI'] = compute_rsi(df['Close'], 14)
    df['OBV'] = compute_obv(df)
    df['MFI'] = compute_mfi(df, 14)

    # Fibonacci
    last_20 = df.tail(20)
    high = last_20['High'].max()
    low = last_20['Low'].min()
    diff = high - low
    fib_levels = {
        "Fib_0.0": round(high, 2),
        "Fib_0.236": round(high - 0.236 * diff, 2),
        "Fib_0.382": round(high - 0.382 * diff, 2),
        "Fib_0.5": round((high + low) / 2, 2),
        "Fib_0.618": round(high - 0.618 * diff, 2),
        "Fib_1.0": round(low, 2)
    }

    # Volume Profile
    bins = np.linspace(low, high, 20)
    df['Price_bin'] = pd.cut(df['Close'], bins)
    volume_profile = df.groupby('Price_bin')['Volume'].sum()
    most_volume_bin = volume_profile.idxmax()
    vp_level = round((most_volume_bin.left + most_volume_bin.right) / 2, 2)

    last_row = df.iloc[-1]
    return {
        "MA20": round(last_row['MA20'], 2),
        "RSI": round(last_row['RSI'], 2),
        "OBV": int(last_row['OBV']),
        "MFI": round(last_row['MFI'], 2),
        "Volume": int(last_row['Volume']),
        "VP_Level": vp_level,
        "Fib_Support": fib_levels['Fib_0.618'],
        "Fib_Resistance": fib_levels['Fib_0.236']
    }

# === Aplikasi Utama ===
def main():
    st.title("📊 Analisa Pisau Jatuh")

    file_url = "https://docs.google.com/spreadsheets/d/1t6wgBIcPEUWMq40GdIH1GtZ8dvI9PZ2v/edit?usp=drive_link"
    df = load_google_drive_excel(file_url)

    if df is None:
        return

    tickers = df['Ticker'].dropna().unique().tolist()
    analysis_date = st.date_input("📅 Tanggal Analisis", value=datetime.today())

    if st.button("🔍 Jalankan Screening"):
        results = []
        progress = st.progress(0)
        info = st.empty()

        for i, ticker in enumerate(tickers):
            data = get_stock_data(ticker, analysis_date)

            if data is not None and len(data) >= 30:
                if detect_pattern(data):
                    papan = df[df['Ticker'] == ticker]['Papan Pencatatan'].values[0]
                    metrics = calculate_metrics(data)

                    results.append({
                        "Ticker": ticker,
                        "Papan Pencatatan": papan,
                        "Last Close": round(data['Close'].iloc[-1], 2),
                        "MA20": metrics["MA20"],
                        "RSI": metrics["RSI"],
                        "OBV": metrics["OBV"],
                        "MFI": metrics["MFI"],
                        "Volume": metrics["Volume"],
                        "VP Level": metrics["VP_Level"],
                        "Fib Support": metrics["Fib_Support"],
                        "Fib Resistance": metrics["Fib_Resistance"]
                    })

            progress.progress((i + 1) / len(tickers))
            info.text(f"Progress: {i + 1}/{len(tickers)}")

        if results:
            st.success("✅ Screening selesai!")
            st.dataframe(pd.DataFrame(results))
        else:
            st.warning("Tidak ada saham yang cocok dengan pola 4 candle.")

if __name__ == "__main__":
    main()
