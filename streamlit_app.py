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
        
        # Validasi: Periksa apakah DataFrame tidak kosong
        if df.empty:
            st.error("The Excel file is empty.")
            return None
        
        # Validasi: Periksa apakah kolom 'Ticker' ada
        if 'Ticker' not in df.columns:
            st.error("The 'Ticker' column is missing in the Excel file.")
            return None
        
        # Debugging: Tampilkan jumlah baris dan kolom
        st.write(f"File successfully loaded with {df.shape[0]} rows and {df.shape[1]} columns.")
        st.success("Excel file successfully read!")
        
        return df
    except Exception as e:
        st.error(f"Error loading Excel file from Google Drive: {e}")
        return None

# Main function
def main():
    st.title("Stock Screening - 4 Candle Pattern")
    
    # URL file Excel di Google Drive
    file_url = "https://docs.google.com/spreadsheets/d/1IeVg6b7UJVE4F8CAtS826YJ11NjYUYty/edit?usp=drive_link&ouid=106044501644618784207&rtpof=true&sd=true"
    
    # Load data dari Google Drive
    st.info("Loading data from Google Drive...")
    df = load_google_drive_excel(file_url)
    
    # Jika file gagal dibaca, hentikan eksekusi
    if df is None or 'Ticker' not in df.columns:
        st.error("Failed to load data or 'Ticker' column is missing.")
        return
    
    # Lanjutkan ke analisis jika file berhasil dibaca
    tickers = df['Ticker'].tolist()
    total_tickers = len(tickers)
    
    # Date input
    analysis_date = st.date_input("Analysis Date", value=datetime.today())
    local_timezone = datetime.now().astimezone().tzinfo
    analysis_date = datetime.combine(analysis_date, datetime.min.time()).replace(tzinfo=local_timezone)
    
    # Ambil data 10 hari terakhir untuk memastikan mendapatkan 4 hari perdagangan aktif
    start_date = analysis_date - timedelta(days=10)
    end_date = analysis_date
    
    # Analyze button
    if st.button("Analyze Stocks"):
        results = []
        progress_bar = st.progress(0)
        progress_text = st.empty()  # Placeholder untuk menampilkan persentase
        
        for i, ticker in enumerate(tickers):
            # Periksa validitas ticker
            if not ticker.endswith(".JK"):
                st.warning(f"Invalid ticker format for {ticker}. Skipping...")
                continue
            
            # Ambil data saham
            data = get_stock_data(ticker, start_date, end_date)
            if data is not None and not data.empty:
                # Ambil 4 hari perdagangan terakhir
                last_4_days_data = data.tail(4)
                
                # Debugging: Tampilkan data yang diterima
                st.write(f"Data for {ticker}:")
                st.write(last_4_days_data)
                
                if detect_pattern(last_4_days_data):
                    results.append(ticker)
            
            # Hitung persentase kemajuan
            progress = (i + 1) / total_tickers
            progress_bar.progress(progress)
            progress_text.text(f"Progress: {int(progress * 100)}%")  # Tampilkan persentase
        
        # Display results
        if results:
            st.subheader("Results")
            st.dataframe(pd.DataFrame(results, columns=["Ticker"]))
        else:
            st.info("No stocks match the pattern.")

# Fungsi untuk mengambil data saham
def get_stock_data(ticker, start_date, end_date):
    try:
        stock = yf.Ticker(f"{ticker}.JK")
        
        # Format tanggal menjadi MM-DD-YYYY untuk yfinance
        start_date_str = start_date.strftime('%m-%d-%Y')
        end_date_str = end_date.strftime('%m-%d-%Y')
        
        # Debugging: Tampilkan rentang tanggal
        st.write(f"Fetching data for {ticker} from {start_date_str} to {end_date_str}")
        
        # Ambil data historis
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
    if len(data) < 4:
        return False
    
    # Ambil 4 candle terakhir
    open_prices = data['Open'].values[-4:]
    close_prices = data['Close'].values[-4:]
    
    # Contoh: Deteksi Bullish Engulfing
    if close_prices[-1] > open_prices[-1] and close_prices[-2] < open_prices[-2]:
        if open_prices[-1] <= close_prices[-2] and close_prices[-1] >= open_prices[-2]:
            return True
    
    return False

if __name__ == "__main__":
    main()
