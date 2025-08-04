import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np
import plotly.graph_objects as go
import requests
from io import BytesIO
from scipy.signal import argrelextrema

# Inisialisasi session state
if 'screening_results' not in st.session_state:
    st.session_state.screening_results = None
if 'selected_ticker' not in st.session_state:
    st.session_state.selected_ticker = None

# 1. Fungsi Deteksi Volume Anomali yang Diperbarui
def detect_volume_anomaly(df, window=20, std_multiplier=2.0, market_comparison=True):
    """
    Mendeteksi anomali volume dengan pendekatan profesional:
    - Analisis statistik (standar deviasi)
    - Perbandingan dengan pasar/indeks
    - Konteks pergerakan harga
    - Pola multi-hari
    """
    # Cek apakah data cukup untuk analisis
    if len(df) < window:
        return {
            "is_anomaly": False,
            "type": "Netral",
            "volume_ratio": 0,
            "market_relative": None
        }
    
    # Hitung rata-rata dan standar deviasi
    df['Volume_MA'] = df['Volume'].rolling(window).mean()
    df['Volume_STD'] = df['Volume'].rolling(window).std()
    
    # Deteksi anomali statistik
    statistical_anomaly = False
    if not pd.isna(df['Volume_MA'].iloc[-1]) and not pd.isna(df['Volume_STD'].iloc[-1]):
        # PERBAIKAN: Ambil nilai tunggal dengan iloc[-1]
        volume_today = df['Volume'].iloc[-1]
        volume_ma = df['Volume_MA'].iloc[-1]
        volume_std = df['Volume_STD'].iloc[-1]
        
        statistical_anomaly = volume_today > (volume_ma + std_multiplier * volume_std)
    
    # Deteksi anomali relatif terhadap pasar
    market_relative_anomaly = False
    market_relative = None
    if market_comparison:
        try:
            market_data = yf.download('^JKSE', period='60d', progress=False)['Volume']
            if not market_data.empty:
                market_avg = market_data.mean()
                market_relative = df['Volume'].iloc[-1] / market_avg
                market_relative_anomaly = market_relative > 2.0
        except Exception as e:
            st.error(f"Error in market data: {str(e)}")
            pass
    
    # Deteksi volume tinggi berkelanjutan
    sustained_anomaly = False
    if len(df) >= window + 3:
        # PERBAIKAN: Ambil nilai numerik bukan Series
        volume_ma_value = df['Volume_MA'].iloc[-1]
        recent_volumes = df['Volume'].tail(3).values
        sustained_anomaly = all(vol > 1.5 * volume_ma_value for vol in recent_volumes)
    
    # Klasifikasi berdasarkan pergerakan harga
    anomaly_type = "Netral"
    volume_ratio = round(df['Volume'].iloc[-1] / df['Volume_MA'].iloc[-1], 2) if not pd.isna(df['Volume_MA'].iloc[-1]) else 0
    
    # PERBAIKAN: Gunakan nilai boolean langsung
    is_anomaly = statistical_anomaly or market_relative_anomaly or sustained_anomaly
    
    if is_anomaly:
        if len(df) >= 2:
            price_change = (df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]
            if abs(price_change) > 0.05:
                anomaly_type = "Breakout" if price_change > 0 else "Breakdown"
            else:
                anomaly_type = "Akumulasi/Distribusi"
        else:
            anomaly_type = "Volume Tinggi"
    
    return {
        "is_anomaly": is_anomaly,
        "type": anomaly_type,
        "volume_ratio": volume_ratio,
        "market_relative": round(market_relative, 2) if market_relative is not None else None
    }

# 2. PERBAIKAN MFI
def compute_mfi(df, period=14):
    """Menghitung Money Flow Index (MFI) dengan metode yang benar"""
    # Hitung Typical Price
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    money_flow = tp * df['Volume']
    
    positive_flow = [0]  # Hari pertama tidak ada perbandingan
    negative_flow = [0]
    
    for i in range(1, len(tp)):
        if tp.iloc[i] > tp.iloc[i-1]:
            positive_flow.append(money_flow.iloc[i-1])
            negative_flow.append(0)
        elif tp.iloc[i] < tp.iloc[i-1]:
            positive_flow.append(0)
            negative_flow.append(money_flow.iloc[i-1])
        else:
            positive_flow.append(money_flow.iloc[i-1])
            negative_flow.append(money_flow.iloc[i-1])
    
    # Konversi ke pandas Series untuk perhitungan rolling
    pos_series = pd.Series(positive_flow)
    neg_series = pd.Series(negative_flow)
    
    # Rolling sum dengan periode tertentu
    pos_mf = pos_series.rolling(window=period, min_periods=1).sum()
    neg_mf = neg_series.rolling(window=period, min_periods=1).sum()
    
    # Hitung MFI dengan penanganan pembagian nol
    ratio = np.where(neg_mf > 0, pos_mf / neg_mf, 1.0)
    mfi = 100 - (100 / (1 + ratio))
    
    return pd.Series(mfi, index=df.index)

def interpret_mfi(mfi_value):
    """Memberikan interpretasi sinyal MFI untuk trading"""
    if mfi_value >= 80:
        return "🔴 Overbought"
    elif mfi_value >= 65:
        return "🟢 Bullish"
    elif mfi_value <= 20:
        return "🟢 Oversold"
    elif mfi_value <= 35:
        return "🔴 Bearish"
    else:
        return "⚪ Neutral"

# 3. PERBAIKAN SUPPORT/RESISTANCE DAN FIBONACCI
def identify_significant_swings(df, window=60, min_swing_size=0.05):
    """Mengidentifikasi swing high dan swing low yang signifikan"""
    # 1. Identifikasi swing points awal
    highs = df['High']
    lows = df['Low']
    
    # Temukan maxima dan minima lokal
    max_idx = argrelextrema(highs.values, np.greater, order=5)[0]
    min_idx = argrelextrema(lows.values, np.less, order=5)[0]
    
    # Ambil swing points dalam window terbaru
    recent_highs = highs.iloc[max_idx][-10:] if len(max_idx) > 0 else pd.Series()
    recent_lows = lows.iloc[min_idx][-10:] if len(min_idx) > 0 else pd.Series()
    
    if len(recent_highs) == 0 or len(recent_lows) == 0:
        # Fallback jika tidak ditemukan swing points
        return df['High'].max(), df['Low'].min()
    
    # 2. Filter berdasarkan signifikansi pergerakan
    significant_highs = []
    significant_lows = []
    
    for i in range(1, len(recent_highs)):
        change = (recent_highs.iloc[i] - recent_highs.iloc[i-1]) / recent_highs.iloc[i-1]
        if abs(change) > min_swing_size:
            significant_highs.append(recent_highs.iloc[i])
    
    for i in range(1, len(recent_lows)):
        change = (recent_lows.iloc[i] - recent_lows.iloc[i-1]) / recent_lows.iloc[i-1]
        if abs(change) > min_swing_size:
            significant_lows.append(recent_lows.iloc[i])
    
    # 3. Pilih swing tertinggi dan terendah yang signifikan
    swing_high = max(significant_highs) if significant_highs else recent_highs.max()
    swing_low = min(significant_lows) if significant_lows else recent_lows.min()
    
    return swing_high, swing_low

def calculate_fibonacci_levels(swing_high, swing_low):
    """Menghitung level Fibonacci retracement yang akurat"""
    diff = swing_high - swing_low
    return {
        'Fib_0.0': round(swing_high, 2),
        'Fib_0.236': round(swing_high - 0.236 * diff, 2),
        'Fib_0.382': round(swing_high - 0.382 * diff, 2),
        'Fib_0.5': round(swing_high - 0.5 * diff, 2),
        'Fib_0.618': round(swing_high - 0.618 * diff, 2),
        'Fib_0.786': round(swing_high - 0.786 * diff, 2),
        'Fib_1.0': round(swing_low, 2)
    }

def calculate_vwap(df):
    """Menghitung Volume Weighted Average Price (VWAP)"""
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    vwap = (tp * df['Volume']).cumsum() / df['Volume'].cumsum()
    return vwap

def find_psychological_levels(close_price):
    """Menemukan level psikologis terdekat"""
    levels = [50, 100, 200, 500, 1000, 2000, 5000]
    closest_level = min(levels, key=lambda x: abs(x - close_price))
    return closest_level

def calculate_support_resistance(data):
    """Menghitung level support dan resistance dengan berbagai metode"""
    df = data.copy()
    current_price = df['Close'].iloc[-1]
    
    # 1. Swing Points dan Fibonacci
    swing_high, swing_low = identify_significant_swings(df.tail(60))
    fib_levels = calculate_fibonacci_levels(swing_high, swing_low)
    
    # 2. Moving Averages
    ma20 = df['Close'].rolling(20).mean().iloc[-1]
    ma50 = df['Close'].rolling(50).mean().iloc[-1]
    
    # 3. VWAP
    vwap = calculate_vwap(df).iloc[-1]
    
    # 4. Psychological Levels
    psych_level = find_psychological_levels(current_price)
    
    # Gabungkan semua level
    support_levels = [
        fib_levels['Fib_0.618'], 
        fib_levels['Fib_0.786'],
        ma20,
        vwap,
        psych_level
    ]
    
    resistance_levels = [
        fib_levels['Fib_0.236'], 
        fib_levels['Fib_0.382'],
        ma50,
        vwap,
        psych_level
    ]
    
    # Filter nilai valid dan ambil yang paling signifikan
    valid_support = [lvl for lvl in support_levels if not np.isnan(lvl) and lvl < current_price]
    valid_resistance = [lvl for lvl in resistance_levels if not np.isnan(lvl) and lvl > current_price]
    
    # Urutkan dan ambil 3 level terdekat
    valid_support.sort(reverse=True)
    valid_resistance.sort()
    
    return {
        'Support': valid_support[:3] if valid_support else [],
        'Resistance': valid_resistance[:3] if valid_resistance else [],
        'Fibonacci': fib_levels
    }

# 4. FUNGSI UTAMA DAN FUNGSI PENDUKUNG
def load_google_drive_excel(file_url):
    try:
        file_id = file_url.split("/d/")[1].split("/")[0]
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url)
        response.raise_for_status()
        
        # Gunakan BytesIO untuk membaca file dari respons
        excel_data = BytesIO(response.content)
        df = pd.read_excel(excel_data, engine='openpyxl')

        if 'Ticker' not in df.columns or 'Papan Pencatatan' not in df.columns:
            st.error("Kolom 'Ticker' dan 'Papan Pencatatan' harus ada di file Excel.")
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
        start_date = end_date - timedelta(days=90)
        data = stock.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
        return data if not data.empty else None
    except Exception as e:
        st.error(f"Gagal mengambil data untuk {ticker}: {e}")
        return None

def detect_pattern(data):
    if len(data) < 4:
        return False
        
    recent = data.tail(4)
    c1, c2, c3, c4 = recent.iloc[0], recent.iloc[1], recent.iloc[2], recent.iloc[3]

    # Kriteria lebih fleksibel
    is_c1_bullish = c1['Close'] > c1['Open'] and (c1['Close'] - c1['Open']) > 0.015 * c1['Open']
    is_c2_bearish = c2['Close'] < c2['Open'] and c2['Close'] < c1['Close']
    is_c3_bearish = c3['Close'] < c3['Open']
    is_c4_bearish = c4['Close'] < c4['Open']
    is_uptrend = data['Close'].iloc[-20:].mean() > data['Close'].iloc[-50:-20].mean() if len(data) >= 50 else False
    is_close_sequence = c2['Close'] > c3['Close'] > c4['Close']

    return all([
        is_c1_bullish,
        is_c2_bearish,
        is_c3_bearish,
        is_c4_bearish,
        is_uptrend,
        is_close_sequence
    ])

def compute_rsi(close, period=14):
    """Menghitung Relative Strength Index (RSI)"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_additional_metrics(data):
    df = data.copy()
    metrics = {}
    
    # Moving Averages
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    
    # Indikator Momentum
    df['RSI'] = compute_rsi(df['Close'])
    df['MFI'] = compute_mfi(df, 14)
    
    # Volume Analysis (menggunakan pendekatan baru)
    volume_analysis = detect_volume_anomaly(df, market_comparison=True)
    
    # Support & Resistance
    sr_levels = calculate_support_resistance(df)
    
    # Interpretasi Indikator
    mfi_value = df['MFI'].iloc[-1] if not df['MFI'].empty and not pd.isna(df['MFI'].iloc[-1]) else np.nan
    mfi_signal = interpret_mfi(mfi_value) if not np.isnan(mfi_value) else "N/A"
    
    last_row = df.iloc[-1]
    
    return {
        "MA20": round(last_row['MA20'], 2) if not np.isnan(last_row['MA20']) else None,
        "MA50": round(last_row['MA50'], 2) if not np.isnan(last_row['MA50']) else None,
        "RSI": round(last_row['RSI'], 2) if not np.isnan(last_row['RSI']) else None,
        "MFI": round(mfi_value, 2) if not np.isnan(mfi_value) else None,
        "MFI_Signal": mfi_signal,
        "Volume": int(last_row['Volume']) if not np.isnan(last_row['Volume']) else None,
        "Volume_Anomali": volume_analysis["is_anomaly"],
        "Anomali_Tipe": volume_analysis["type"],
        "Volume_Ratio": volume_analysis["volume_ratio"],
        "Support": sr_levels['Support'],
        "Resistance": sr_levels['Resistance'],
        "Fibonacci": sr_levels['Fibonacci']
    }

def main():
    st.title("📊 Stock Screener - Pisau Jatuh SHZ 2nd Gen Edition")

    file_url = "https://docs.google.com/spreadsheets/d/1t6wgBIcPEUWMq40GdIH1GtZ8dvI9PZ2v/edit?usp=drive_link"
    df = load_google_drive_excel(file_url)

    if df is None or 'Ticker' not in df.columns:
        return

    tickers = df['Ticker'].dropna().unique().tolist()
    analysis_date = st.date_input("📅 Tanggal Analisis", value=datetime.today())

    # Tombol screening
    if st.button("🔍 Mulai Screening"):
        results = []
        progress_bar = st.progress(0)
        progress_text = st.empty()
        total_tickers = len(tickers)

        for i, ticker in enumerate(tickers):
            data = get_stock_data(ticker, analysis_date)

            if data is not None and len(data) >= 50:
                if detect_pattern(data):
                    metrics = calculate_additional_metrics(data)
                    papan = df[df['Ticker'] == ticker]['Papan Pencatatan'].values[0]
                    fib = metrics["Fibonacci"]

                    results.append({
                        "Ticker": ticker,
                        "Papan": papan,
                        "Last Close": round(data['Close'].iloc[-1], 2),
                        "MA20": metrics["MA20"],
                        "MA50": metrics["MA50"],
                        "RSI": metrics["RSI"],
                        "MFI": metrics["MFI"],
                        "MFI Signal": metrics["MFI_Signal"],
                        "Vol Anomali": "🚨 Ya" if metrics["Volume_Anomali"] else "-",
                        "Anomali Tipe": metrics["Anomali_Tipe"],
                        "Vol Ratio": metrics["Volume_Ratio"],
                        "Volume": metrics["Volume"],
                        "Support": " | ".join([f"{s:.2f}" for s in metrics["Support"]]),
                        "Resistance": " | ".join([f"{r:.2f}" for r in metrics["Resistance"]]),
                        "Fib 0.382": fib['Fib_0.382'],
                        "Fib 0.5": fib['Fib_0.5'],
                        "Fib 0.618": fib['Fib_0.618']
                    })

            progress = (i + 1) / total_tickers
            progress_bar.progress(progress)
            progress_text.text(f"Progress: {int(progress * 100)}% - Memproses {ticker} ({i+1}/{total_tickers})")

        if results:
            st.session_state.screening_results = pd.DataFrame(results)
            st.session_state.selected_ticker = None
            st.success(f"✅ Ditemukan {len(results)} saham yang memenuhi kriteria")
        else:
            st.warning("Tidak ada saham yang cocok dengan pola.")

    # Tampilkan hasil screening jika ada
    if st.session_state.screening_results is not None:
        st.subheader("✅ Saham yang Memenuhi Kriteria")
        st.dataframe(st.session_state.screening_results)
        
        # Dropdown untuk memilih saham
        ticker_list = st.session_state.screening_results['Ticker'].tolist()
        selected_ticker = st.selectbox(
            "Pilih Saham untuk Detail",
            options=ticker_list,
            index=ticker_list.index(st.session_state.selected_ticker) if st.session_state.selected_ticker in ticker_list else 0,
            key='ticker_selector'
        )
        
        # Simpan ticker yang dipilih di session state
        st.session_state.selected_ticker = selected_ticker
        
        # Tombol untuk menampilkan detail
        if st.button("Tampilkan Analisis Detail"):
            if st.session_state.selected_ticker:
                show_stock_details(st.session_state.selected_ticker, analysis_date)

def show_stock_details(ticker, end_date):
    """Menampilkan detail analisis teknis untuk saham terpilih"""
    data = get_stock_data(ticker, end_date)
    if data is None or data.empty:
        st.warning(f"Data untuk {ticker} tidak tersedia")
        return
        
    st.subheader(f"Analisis Teknis: {ticker}")
    
    # Buat chart
    fig = go.Figure()
    
    # Tambahkan candlestick
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='Candlestick'
    ))
    
    # Tambahkan MA
    data['MA20'] = data['Close'].rolling(20).mean()
    data['MA50'] = data['Close'].rolling(50).mean()
    fig.add_trace(go.Scatter(
        x=data.index, 
        y=data['MA20'], 
        name='MA20',
        line=dict(color='blue', width=1)
    ))
    fig.add_trace(go.Scatter(
        x=data.index, 
        y=data['MA50'], 
        name='MA50',
        line=dict(color='orange', width=1)
    ))
    
    try:
        # Support/Resistance dan Fibonacci
        sr = calculate_support_resistance(data)
        fib = sr['Fibonacci']
        
        # Tambahkan level Support/Resistance
        for level in sr['Support']:
            fig.add_hline(
                y=level, 
                line_dash="dash", 
                line_color="green",
                annotation_text=f"Support: {level:.2f}",
                annotation_position="bottom right"
            )
        for level in sr['Resistance']:
            fig.add_hline(
                y=level, 
                line_dash="dash", 
                line_color="red",
                annotation_text=f"Resistance: {level:.2f}",
                annotation_position="top right"
            )
        
        # Tambahkan level Fibonacci
        for key, value in fib.items():
            if "Fib" in key:
                fig.add_hline(
                    y=value,
                    line_dash="dot",
                    line_color="purple",
                    annotation_text=f"{key}: {value:.2f}",
                    annotation_position="top left" if "0." in key else "bottom left"
                )
    except Exception as e:
        st.warning(f"Gagal menghitung support/resistance: {e}")
    
    # Layout chart
    fig.update_layout(
        title=f"{ticker} Price Analysis",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Tampilkan indikator tambahan
    st.subheader("Indikator Teknikal")
    try:
        metrics = calculate_additional_metrics(data)
        fib = metrics.get("Fibonacci", {})
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("MA20", f"{metrics.get('MA20', 0):.2f}")
        col2.metric("MA50", f"{metrics.get('MA50', 0):.2f}")
        col3.metric("RSI", f"{metrics.get('RSI', 0):.2f}")
        col4.metric("MFI", f"{metrics.get('MFI', 0):.2f}", metrics.get('MFI_Signal', 'N/A'))
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Volume", f"{metrics.get('Volume', 0):,}")
        col2.metric("Volume Anomali", 
                   "Ya" if metrics.get('Volume_Anomali', False) else "Tidak",
                   f"{metrics.get('Anomali_Tipe', '')}")
        col3.metric("Volume Ratio", f"{metrics.get('Volume_Ratio', 0):.2f}x")
        
        st.subheader("Level Penting")
        st.write(f"**Support:** {' | '.join([f'{s:.2f}' for s in metrics.get('Support', [])])}")
        st.write(f"**Resistance:** {' | '.join([f'{r:.2f}' for r in metrics.get('Resistance', [])])}")
        
        st.subheader("Level Fibonacci")
        fib_cols = st.columns(7)
        fib_levels = ['Fib_0.0', 'Fib_0.236', 'Fib_0.382', 'Fib_0.5', 'Fib_0.618', 'Fib_0.786', 'Fib_1.0']
        for i, level in enumerate(fib_levels):
            fib_cols[i].metric(level, f"{fib.get(level, 0):.2f}")
    except Exception as e:
        st.error(f"Gagal menampilkan indikator: {e}")

if __name__ == "__main__":
    main()
