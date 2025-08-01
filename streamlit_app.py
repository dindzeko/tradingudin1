import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from ta.momentum import RSIIndicator, MoneyFlowIndex
from ta.trend import ADXIndicator

# ========= Helper Function ===========

def compute_rsi(series, period=14):
    return RSIIndicator(series, window=period).rsi()

def compute_mfi(high, low, close, volume, period=14):
    return MoneyFlowIndex(high=high, low=low, close=close, volume=volume, window=period).money_flow_index()

def compute_obv(close, volume):
    obv = [volume[0]]
    for i in range(1, len(close)):
        if close[i] > close[i - 1]:
            obv.append(obv[-1] + volume[i])
        elif close[i] < close[i - 1]:
            obv.append(obv[-1] - volume[i])
        else:
            obv.append(obv[-1])
    return obv

def interpret_obv(obv_list):
    if len(obv_list) < 11:
        return "Netral"
    recent_obv = obv_list[-1]
    avg_past_obv = np.mean(obv_list[-11:-1])
    if recent_obv > avg_past_obv * 1.02:
        return "Tekanan Beli"
    elif recent_obv < avg_past_obv * 0.98:
        return "Tekanan Jual"
    else:
        return "Netral"

def detect_volume_anomaly(volume_series, factor=1.5):
    if len(volume_series) < 21:
        return "-"
    avg_volume = volume_series[:-1].tail(20).mean()
    latest_volume = volume_series.iloc[-1]
    return "🔥 Ya" if latest_volume > avg_volume * factor else "-"

def interpret_adx(adx_value):
    if pd.isna(adx_value):
        return "None"
    elif adx_value < 20:
        return "Tren Lemah"
    elif 20 <= adx_value <= 40:
        return "Tren Sedang"
    else:
        return "Tren Kuat"

def calculate_additional_metrics(data):
    df = data.copy()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['RSI'] = compute_rsi(df['Close'], 14)
    df['MFI'] = compute_mfi(df['High'], df['Low'], df['Close'], df['Volume'], 14)
    df['OBV_raw'] = compute_obv(df['Close'], df['Volume'])
    df['OBV_Interp'] = interpret_obv(df['OBV_raw'])
    try:
        adx_indicator = ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=14)
        df['ADX'] = adx_indicator.adx()
        adx_value = df['ADX'].iloc[-1]
        adx_interpretation = interpret_adx(adx_value)
    except:
        adx_interpretation = "None"
    vol_anomaly = detect_volume_anomaly(df['Volume'])
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
    bin_low = most_volume_bin.left
    bin_high = most_volume_bin.right
    volume_support_resist = round((bin_low + bin_high) / 2, 2)
    last_row = df.iloc[-1]
    return {
        "Last Close": round(last_row['Close'], 2),
        "MA20": round(last_row['MA20'], 2) if not np.isnan(last_row['MA20']) else None,
        "RSI": round(last_row['RSI'], 2) if not np.isnan(last_row['RSI']) else None,
        "MFI": round(last_row['MFI'], 2) if not np.isnan(last_row['MFI']) else None,
        "ADX": adx_interpretation,
        "Vol Anomal": vol_anomaly,
        "Volume": int(last_row['Volume']),
        "OBV": df['OBV_Interp'].iloc[-1],
        "Fib Levels": fib_levels,
        "Vol Profile": volume_support_resist
    }

def main():
    st.title("📈 Analisa Saham Pola 4 Candle + Indikator")
    uploaded_file = st.file_uploader("Upload hasil screening saham (.xlsx)", type=['xlsx'])
    if uploaded_file:
        screener_df = pd.read_excel(uploaded_file)
        results = []
        for _, row in screener_df.iterrows():
            ticker = row['Ticker']
            try:
                df = yf.download(ticker + ".JK", period="60d", interval="1d", progress=False)
                if df.empty or len(df) < 40:
                    continue
                analysis = calculate_additional_metrics(df)
                combined = {
                    "Ticker": ticker,
                    "Papan": row.get("Papan", "-"),
                    **{k: analysis[k] for k in ["Last Close", "MA20", "RSI", "MFI", "ADX", "Vol Anomal", "Volume", "OBV"]},
                }
                results.append(combined)
            except Exception as e:
                st.warning(f"Error untuk saham {ticker}: {str(e)}")
        if results:
            df_result = pd.DataFrame(results)
            st.success("✅ Saham yang Memenuhi Kriteria")
            st.dataframe(df_result, use_container_width=True)

if __name__ == "__main__":
    main()
