import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Fungsi untuk membaca data dari Google Spreadsheet (tanpa API)
def load_google_sheet(sheet_url):
    try:
        # Ubah URL menjadi format CSV
        csv_url = sheet_url.replace("/edit?usp=sharing", "/gviz/tq?tqx=out:csv")
        df = pd.read_csv(csv_url)
        if 'Ticker' not in df.columns:
            st.error("The 'Ticker' column is missing in the Google Sheet.")
            return None
        return df
    except Exception as e:
        st.error(f"Error loading Google Sheet: {e}")
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

# Main function
def main():
    st.title("Stock Screening - 4 Candle Pattern")
    
    # URL Google Spreadsheet
    sheet_url = "https://docs.google.com/spreadsheets/d/1daPWAAPAlPzKxlG9Hf8nL01OnlnrX_ICFlWzMosnZW0/edit?gid=2116843523#gid=2116843523"
    
    # Load data dari Google Spreadsheet
    st.info("Loading data from Google Spreadsheet...")
    df = load_google_sheet(sheet_url)
    if df is None or 'Ticker' not in df.columns:
        st.error("Failed to load data or 'Ticker' column is missing.")
        return
    
    tickers = df['Ticker'].tolist()
    
    # Date input
    analysis_date = st.date_input("Analysis Date", value=datetime.today())
    start_date = analysis_date - timedelta(days=4)
    end_date = analysis_date
    
    # Analyze button
    if st.button("Analyze Stocks"):
        results = []
        total_tickers = len(tickers)
        progress_bar = st.progress(0)
        
        for i, ticker in enumerate(tickers):
            data = get_stock_data(ticker, start_date, end_date)
            if data is not None and not data.empty:
                if detect_pattern(data):
                    results.append(ticker)
            # Update progress bar
            progress_bar.progress((i + 1) / total_tickers)
        
        # Display results
        if results:
            st.subheader("Results")
            st.dataframe(pd.DataFrame(results, columns=["Ticker"]))
        else:
            st.info("No stocks match the pattern.")

if __name__ == "__main__":
    main()
