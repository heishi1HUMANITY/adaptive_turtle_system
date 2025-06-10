import os
import sys
import argparse
import time
import pandas as pd
import requests
import io

def fetch_forex_data(year, month, symbol, api_key):
    """
    Fetches historical forex data from Alpha Vantage using FX_INTRADAY_EXTENDED.
    Symbol should be in format like 'USDJPY'.
    On error, prints to stderr and returns None.
    """
    url = (f'https://www.alphavantage.co/query?'
           f'function=FX_INTRADAY_EXTENDED&symbol={symbol}&interval=1min&slice=year{year}month{month}&apikey={api_key}')

    # This informational message can go to stdout as it's part of normal operation logging.
    print(f"Fetching intraday data for {symbol} ({year}-{month:02d}) using API key {api_key[:5]}...")

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        csv_raw_data = response.content.decode('utf-8')

        if not csv_raw_data.strip() or \
           'Error Message' in csv_raw_data or \
           ('Information' in csv_raw_data and 'API call frequency' in csv_raw_data):
            print(f"  -> {year}年{month}月のデータ取得に失敗、またはデータが存在しません。", file=sys.stderr)
            api_response_snippet = csv_raw_data.splitlines()[0] if csv_raw_data.strip() else "Empty response"
            print(f"     API Response: {api_response_snippet[:200]}", file=sys.stderr)
            return None

        df = pd.read_csv(io.StringIO(csv_raw_data))

        if df.empty:
            print(f"  -> {year}年{month}月のデータは空です。", file=sys.stderr) # Corrected message
            return None

        df.rename(columns={'time': 'Timestamp', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
        df['Volume'] = 0
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        df = df[['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']]

        # Print the number of records fetched to stdout
        print(f"  -> {len(df)}件のデータを取得しました。")
        return df

    except requests.exceptions.RequestException as e:
        print(f"  -> APIリクエスト中にエラーが発生しました: {e}", file=sys.stderr)
        return None
    except pd.errors.EmptyDataError: # Specific error for pd.read_csv if data is empty after all
        print(f"  -> CSVデータが空または不正です。APIから有効なデータが返されませんでした。", file=sys.stderr)
        if 'csv_raw_data' in locals():
             print(f"     Raw CSV Data Snippet: {csv_raw_data[:200]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  -> データ処理中に予期せぬエラーが発生しました: {e}", file=sys.stderr)
        if 'csv_raw_data' in locals():
             print(f"     Raw CSV Data Snippet (if available): {csv_raw_data[:200]}", file=sys.stderr)
        return None


def main(args):
    # These initial messages can be stdout
    print(f"Starting data collection for Symbol: {args.symbol}, Year: {args.year}, Month: {args.month}")
    print(f"Output directory: {args.output_dir}")

    fetched_data_df = fetch_forex_data(args.year, args.month, args.symbol, args.api_key)

    if fetched_data_df is None:
        print(f"{args.symbol} のデータ取得または処理に失敗しました。詳しくは上記のエラーメッセージをご確認ください。", file=sys.stderr)
        sys.exit(1)

    if fetched_data_df.empty: # Should be caught by fetch_forex_data now, but as a safeguard
        print(f"{args.symbol} - {args.year}-{args.month:02d} のデータが見つかりませんでした（空のデータセット）。", file=sys.stderr)
        sys.exit(1)

    try:
        # Ensure output directory exists
        # This can also go to stdout as it's a setup step, not an error yet.
        if not os.path.exists(args.output_dir):
            print(f"Creating output directory: {args.output_dir}")
            os.makedirs(args.output_dir) # This can raise OSError

        # Sort data by Timestamp before calculating dates and saving
        fetched_data_df.sort_values(by='Timestamp', inplace=True)

        start_date = fetched_data_df['Timestamp'].min().strftime('%Y%m%d')
        end_date = fetched_data_df['Timestamp'].max().strftime('%Y%m%d')
        output_filename = f'{args.symbol}_M1_{start_date}_{end_date}.csv'
        output_path = os.path.join(args.output_dir, output_filename)

        fetched_data_df.to_csv(output_path, index=False)
        # Success message to stdout
        print(f"Data successfully saved to {output_path}")

    except OSError as e: # Catch errors from os.makedirs
        print(f"出力ディレクトリの作成中にエラーが発生しました ({args.output_dir}): {e}", file=sys.stderr)
        sys.exit(1)
    except AttributeError as e: # Catch errors if Timestamp column is missing (e.g. from min/max)
        print(f"データ処理エラー: 'Timestamp'カラムが見つからないか、データが不正です。 {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e: # Catch errors from to_csv or other operations
        print(f"CSVファイルへの保存中にエラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)

    # This is a standard operational log, stdout is fine.
    print("Waiting for 15 seconds to respect API rate limits...")
    time.sleep(15)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fetch and save forex data from Alpha Vantage for a specific month using FX_INTRADAY_EXTENDED.")
    # Argument parser errors automatically go to stderr and exit.
    parser.add_argument("--symbol", type=str, required=True, help="Trading symbol (e.g., USDJPY)")
    parser.add_argument("--year", type=int, required=True, help="Year for data fetching")
    parser.add_argument("--month", type=int, required=True, help="Month for data fetching")
    parser.add_argument("--api-key", type=str, required=True, help="Alpha Vantage API key")
    parser.add_argument("--output-dir", type=str, required=True, help="Directory to save the output CSV file")

    args = parser.parse_args()
    main(args)
