import os
import sys
import argparse
import time
import pandas as pd
import requests
import io
import json # Added import

def fetch_forex_data(symbol, api_key):
    """
    Fetches all available historical intraday data from Alpha Vantage using TIME_SERIES_INTRADAY
    with outputsize=full.
    Symbol should be in format like 'USDJPY' (though this endpoint is typically for stocks).
    On error, prints to stderr and returns None.
    """
    # Symbol validation can be kept if it's still relevant for the expected format.
    # if len(symbol) < 1: # Example: Basic check for non-empty symbol
    #     print(f"  -> Invalid symbol: {symbol}. Symbol cannot be empty.", file=sys.stderr)
    #     return None

    url = (f'https://www.alphavantage.co/query?'
           f'function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=1min'
           f'&outputsize=full&apikey={api_key}') # Removed month parameter

    # This informational message can go to stdout as it's part of normal operation logging.
    print(f"Fetching full TIME_SERIES_INTRADAY data for {symbol} using API key {api_key[:5]}...")

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        response_text = response.content.decode('utf-8')

        try:
            json_response = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"  -> Failed to parse API response as JSON: {e}", file=sys.stderr)
            print(f"     API Response Snippet: {response_text[:1000]}", file=sys.stderr)
            return None

        # Check for error messages within the JSON response itself
        if isinstance(json_response, dict) and "Error Message" in json_response:
            print(f"  -> API Error: {json_response['Error Message']}", file=sys.stderr)
            # Print full response if it's an error message, as it might be short and informative
            print(f"     Full API Response: {response_text}", file=sys.stderr)
            return None

        # Check for "Information" messages (e.g., premium endpoint, API limits)
        if isinstance(json_response, dict) and "Information" in json_response:
            information_message = str(json_response["Information"])
            # Check for premium endpoint message
            if "premium endpoint" in information_message.lower():
                print(f"  -> API Error: This is a premium endpoint. Subscription required for {symbol}.", file=sys.stderr)
                print(f"     API Response: {response_text[:1000]}", file=sys.stderr)
                return None
            # Check for API call frequency limit message
            if "api call frequency" in information_message.lower():
                 print(f"  -> API Error: API call frequency limit reached. Message: {information_message}", file=sys.stderr)
                 print(f"     API Response: {response_text[:1000]}", file=sys.stderr)
                 return None
            # Handle other informational messages that might indicate no data or other issues
            # For example, if the "Information" message implies no data was found.
            # This part might need refinement based on observed "Information" messages.
            print(f"  -> API Information: {information_message}", file=sys.stderr)
            # If an "Information" message is present, it often means no valid time series data will follow.
            # Consider returning None unless specific "Information" messages are known to be benign.
            print(f"     (Assuming this information means no data for {symbol})") # Removed year_month_str
            return None


        # Extract Meta Data
        meta_data = json_response.get("Meta Data")
        if not meta_data or not isinstance(meta_data, dict):
            print(f"  -> API Error: 'Meta Data' not found or not in expected format in JSON response for {symbol}.", file=sys.stderr) # Removed year_month_str
            print(f"     JSON Response Snippet: {str(json_response)[:1000]}", file=sys.stderr)
            return None

        # Determine the time series key (e.g., "Time Series (1min)")
        # The interval used in the request is '1min'.
        interval_from_meta = meta_data.get("4. Interval", "1min") # Default to 1min

        # Construct possible keys. TIME_SERIES_INTRADAY can be used for FX by some,
        # where AlphaVantage might use "Time Series FX (interval)"
        # or for stocks "Time Series (interval)".
        possible_ts_keys = [
            f"Time Series ({interval_from_meta})",
            f"Time Series FX ({interval_from_meta})", # More specific for FX if API uses it
        ]

        time_series_data = None
        for key_to_try in possible_ts_keys:
            if key_to_try in json_response:
                time_series_data = json_response[key_to_try]
                break

        if not time_series_data or not isinstance(time_series_data, dict) or not time_series_data:
            print(f"  -> API Error: Time series data not found or is empty in JSON response for {symbol}. Tried keys: {possible_ts_keys}", file=sys.stderr) # Removed year_month_str
            print(f"     JSON Response Snippet: {str(json_response)[:1000]}", file=sys.stderr)
            return None

        # Convert time series data to DataFrame
        df = pd.DataFrame.from_dict(time_series_data, orient='index')

        # Rename columns
        rename_map = {
            '1. open': 'Open', '2. high': 'High',
            '3. low': 'Low', '4. close': 'Close', '5. volume': 'Volume'
        }
        df.rename(columns=rename_map, inplace=True)

        # Convert index to datetime (timestamps from API) and sort
        df.index = pd.to_datetime(df.index)
        df.sort_index(ascending=True, inplace=True) # Sort by timestamp ascending

        # Reset index to make 'Timestamp' a column
        df.reset_index(inplace=True)
        df.rename(columns={'index': 'Timestamp'}, inplace=True)

        # Ensure OHLC columns are numeric
        ohlc_cols = ['Open', 'High', 'Low', 'Close']
        for col in ohlc_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Drop rows where essential OHLC data conversion failed
        df.dropna(subset=ohlc_cols, inplace=True)

        # Ensure Volume column exists and is numeric, fill with 0 if not present or conversion fails
        if 'Volume' not in df.columns:
            df['Volume'] = 0
        else:
            df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce').fillna(0)

        # Select and order final columns
        df = df[['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']]

        if df.empty:
            print(f"  -> Data for {symbol} is empty after processing JSON.", file=sys.stderr) # Removed year_month_str
            return None

        print(f"  -> {len(df)}件のデータをJSONから取得・処理しました。")
        return df

    except requests.exceptions.RequestException as e:
        print(f"  -> APIリクエスト中にエラーが発生しました: {e}", file=sys.stderr)
        return None
    # Removed pd.errors.EmptyDataError as CSV parsing is no longer the primary path.
    # Other specific pandas errors could be caught here if necessary during DataFrame manipulation.
    except Exception as e: # General catch-all for other unexpected errors during processing
        print(f"  -> データ処理中に予期せぬエラーが発生しました ({type(e).__name__}): {e}", file=sys.stderr)
        # If response_text is available, print a snippet. It might not be if error is pre-request.
        if 'response_text' in locals():
             print(f"     Original Response Text Snippet (if available): {response_text[:1000]}", file=sys.stderr)
        return None


def main(args):
    # These initial messages can be stdout
    print(f"Starting data collection for Symbol: {args.symbol} (full timeseries)") # Updated print
    print(f"Output directory: {args.output_dir}")

    fetched_data_df = fetch_forex_data(args.symbol, args.api_key) # Updated call

    if fetched_data_df is None:
        print(f"{args.symbol} のデータ取得または処理に失敗しました。詳しくは上記のエラーメッセージをご確認ください。", file=sys.stderr) # Message is general enough
        sys.exit(1)

    if fetched_data_df.empty: # Should be caught by fetch_forex_data now, but as a safeguard
        print(f"{args.symbol} のデータが見つかりませんでした（空のデータセット）。", file=sys.stderr) # Updated message
        sys.exit(1)

    try:
        # Ensure output directory exists
        # This can also go to stdout as it's a setup step, not an error yet.
        if not os.path.exists(args.output_dir):
            print(f"Creating output directory: {args.output_dir}")
            os.makedirs(args.output_dir) # This can raise OSError

        # Sort data by Timestamp before saving (still good practice)
        fetched_data_df.sort_values(by='Timestamp', inplace=True)

        # Use fixed output filename
        output_filename = f'{args.symbol}_M1_full_timeseries.csv' # Changed filename
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
    parser = argparse.ArgumentParser(description="Fetch and save full historical intraday forex data from Alpha Vantage using TIME_SERIES_INTRADAY.") # Updated description
    # Argument parser errors automatically go to stderr and exit.
    parser.add_argument("--symbol", type=str, required=True, help="Trading symbol (e.g., USDJPY)")
    # Removed --year and --month arguments
    parser.add_argument("--api-key", type=str, required=True, help="Alpha Vantage API key")
    parser.add_argument("--output-dir", type=str, required=True, help="Directory to save the output CSV file")

    args = parser.parse_args()
    main(args)
