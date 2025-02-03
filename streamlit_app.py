import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Fungsi untuk membaca file Excel
def upload_file():
    file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
    if file_path:
        try:
            df = pd.read_excel(file_path)
            tickers = df['Ticker'].tolist()
            messagebox.showinfo("Success", "File uploaded successfully!")
            return tickers
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read file: {e}")
    return None

# Fungsi untuk mengambil data saham
def get_stock_data(ticker, start_date, end_date):
    try:
        stock = yf.Ticker(f"{ticker}.JK")
        data = stock.history(start=start_date, end=end_date)
        if data.empty:
            print(f"No data found for {ticker} in the given date range.")
        return data
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

# Fungsi untuk mendeteksi pola berdasarkan 4 candle
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

# Fungsi untuk melakukan analisis
def analyze_stocks():
    tickers = upload_file()
    if not tickers:
        return

    analysis_date = entry_date.get()
    try:
        analysis_date = datetime.strptime(analysis_date, "%Y-%m-%d")
        start_date = analysis_date - timedelta(days=4)
        end_date = analysis_date

        # Pastikan tanggal tidak lebih dari hari ini
        if end_date > datetime.today():
            messagebox.showerror("Error", "Analysis date cannot be in the future.")
            return

        results = []
        total_tickers = len(tickers)
        progress_bar['maximum'] = total_tickers
        progress_bar['value'] = 0
        progress_label.config(text="0%")

        for i, ticker in enumerate(tickers):
            data = get_stock_data(ticker, start_date, end_date)
            if data is not None and not data.empty:
                print(f"Data for {ticker}:")
                print(data[['Open', 'High', 'Low', 'Close']])
                if detect_pattern(data):
                    results.append(ticker)
                    print(f"{ticker} matches the pattern.")
                else:
                    print(f"{ticker} does not match the pattern.")
            else:
                print(f"No data available for {ticker}.")

            # Update progress bar and label
            progress_bar['value'] = i + 1
            progress_percent = int((i + 1) / total_tickers * 100)
            progress_label.config(text=f"{progress_percent}%")
            root.update_idletasks()  # Update GUI

        # Menampilkan hasil dalam tabel
        result_df = pd.DataFrame(results, columns=["Ticker"])
        result_text.delete(1.0, tk.END)
        if not result_df.empty:
            result_text.insert(tk.END, result_df.to_string(index=False))
        else:
            result_text.insert(tk.END, "No stocks match the pattern.")

        # Reset progress bar after analysis
        progress_bar['value'] = 0
        progress_label.config(text="0%")
    except ValueError:
        messagebox.showerror("Error", "Invalid date format. Please use YYYY-MM-DD.")

# Membuat GUI
root = tk.Tk()
root.title("Stock Screening - 4 Candle Pattern")

# Label dan Entry untuk tanggal analisis
label_date = tk.Label(root, text="Analysis Date (YYYY-MM-DD):")
label_date.grid(row=0, column=0, padx=10, pady=10)
entry_date = tk.Entry(root)
entry_date.grid(row=0, column=1, padx=10, pady=10)

# Tombol untuk upload file dan analisis
button_upload = tk.Button(root, text="Upload Ticker File and Analyze", command=analyze_stocks)
button_upload.grid(row=1, column=0, columnspan=2, padx=10, pady=10)

# Progress bar dan label persentase
progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress_bar.grid(row=2, column=0, columnspan=2, padx=10, pady=10)
progress_label = tk.Label(root, text="0%")
progress_label.grid(row=3, column=0, columnspan=2, padx=10, pady=5)

# Text widget untuk menampilkan hasil
result_text = tk.Text(root, height=10, width=50)
result_text.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

root.mainloop()
