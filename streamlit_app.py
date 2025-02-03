import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Fungsi untuk membaca data dari Google Drive (file Excel)
def load_google_drive_excel(file_url):
    try:
        # Ubah URL Google Drive menjadi URL unduhan langsung
        file_id = file_url.split("/d/")[1].split("/")[0]
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        # Baca file Excel menggunakan pandas dengan engine openpyxl
        df = pd.read_excel(download_url, engine='openpyxl')
        if 'Ticker' not in df.columns:
            st.error("The 'Ticker' column is missing in the Excel file.")
            return None
        return df
    except Exception as e:
        st.error(f"Error loading Excel file from Google Drive: {e}")
        return None

# Fungsi untuk mengambil data saham
def get_stock_data(ticker, start_date, end_date):
    try:
        stock = yf.Ticker(f"{ticker}.JK")
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        data = stock.history(start=start_date_str, end=end_date_str)
        if data.empty:
            st.warning(f"No data found for {ticker} in the given date range.")
            return None
        return data
    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {str(e)}")
        return None

# Fungsi untuk mendeteksi pola berdasarkan 4 candle
def detect_pattern(data):
    if len(data) >= 4:
        # Candle 1: Bullish dengan body besar
        candle1 = data.iloc[-4]
        is_candle1_bullish = candle1['Close'] > candle1['Open']
        is_candle1_large_body = (candle1['Close'] - candle1['Open']) > 0.02 * candle1['Open']  # Body besar > 2%
        
        # Candle 2: Bearish dan ditutup lebih rendah dari candle 1
        candle2 = data.iloc[-3]
        is_candle2_bearish = candle2['Close'] < candle2['Open']
        is_candle2_lower_than_candle1 = candle2['Close'] < candle1['Close']
        
        # Candle 3: Bearish
        candle3 = data.iloc[-2]
        is_candle3_bearish = candle3['Close'] < candle3['Open']
        
        # Candle 4: Bearish
        candle4 = data.iloc[-1]
        is_candle4_bearish = candle4['Close'] < candle4['Open']
        
        # Pastikan pola muncul di tren naik (harga candle 4 lebih rendah dari candle 1)
        is_uptrend = candle4['Close'] < candle1['Close']
        
        # Pastikan close candle 2 > close candle 3 > close candle 4
        is_close_sequence = candle2['Close'] > candle3['Close'] > candle4['Close']
        
        # Semua kondisi harus terpenuhi
        return (
            is_candle1_bullish and
            is_candle1_large_body and
            is_candle2_bearish and
            is_candle2_lower_than_candle1 and
            is_candle3_bearish and
            is_candle4_bearish and
            is_uptrend and
            is_close_sequence
        )
    return False

# Main function
def main():
    st.title("Stock Screening - 4 Candle ")
    
    # URL file Excel di Google Drive
    file_url = "https://docs.google.com/spreadsheets/d/1t6wgBIcPEUWMq40GdIH1GtZ8dvI9PZ2v/edit?usp=drive_link&ouid=106044501644618784207&rtpof=true&sd=true"
    
    # Load data dari Google Drive
    st.info("Loading data from Google Drive...")
    df = load_google_drive_excel(file_url)
    if df is None or 'Ticker' not in df.columns:
        st.error("Failed to load data or 'Ticker' column is missing.")
        return
    
    tickers = df['Ticker'].tolist()
    total_tickers = len(tickers)
    
    # Date input
    analysis_date = st.date_input("Analysis Date", value=datetime.today())
    start_date = analysis_date - timedelta(days=4)
    end_date = analysis_date
    
    # Analyze button
    if st.button("Analyze Stocks"):
        results = []
        progress_bar = st.progress(0)
        progress_text = st.empty()  # Placeholder untuk menampilkan persentase
        
        for i, ticker in enumerate(tickers):
            data = get_stock_data(ticker, start_date, end_date)
            if data is not None and not data.empty:
                if detect_pattern(data):
                    # Simpan hasil saham yang memenuhi kriteria
                    results.append({
                        "Ticker": ticker,
                        "Last Close": data['Close'][-1],
                        "Pattern Detected": "unconfirmed Mathold"
                    })
            
            # Hitung persentase kemajuan
            progress = (i + 1) / total_tickers
            progress_bar.progress(progress)
            progress_text.text(f"Progress: {int(progress * 100)}%")  # Tampilkan persentase
        
        # Display results
        if results:
            st.subheader("Results: Stocks Meeting Criteria")
            results_df = pd.DataFrame(results)
            st.dataframe(results_df)
        else:
            st.info("No stocks match the pattern.")

if __name__ == "__main__":
    main()
