import pandas as pd
import data_loader
import config_loader
import trading_logic # Specifically run_strategy
import performance_analyzer # Specifically calculate_all_kpis, generate_text_report

def main():
    """
    Main function to run the backtesting process.
    """
    print("Starting backtest process...")

    try:
        # 1. Load Configuration
        print("Loading configuration...")
        config = config_loader.load_config('config.json')
        if not config:
            print("Error: Configuration file could not be loaded. Exiting.")
            return

        # 2. Load Historical Data
        print("Loading historical data...")
        raw_data_df = data_loader.load_csv_data('historical_data.csv') # Assumes 'Timestamp' is a column
        if raw_data_df.empty:
            print("Error: Historical data file could not be loaded or is empty. Exiting.")
            return

        # Convert 'Timestamp' column to datetime objects if not already
        if 'Timestamp' not in raw_data_df.columns:
            print("Error: 'Timestamp' column not found in historical_data.csv. Exiting.")
            return

        try:
            raw_data_df['Timestamp'] = pd.to_datetime(raw_data_df['Timestamp'])
        except Exception as e:
            print(f"Error converting 'Timestamp' column to datetime: {e}. Exiting.")
            return

        raw_data_df.set_index('Timestamp', inplace=True)

        # 3. Prepare historical_data_dict
        historical_data_dict = {}
        traded_markets = config.get('markets', [])

        if not traded_markets:
            print("Error: No markets specified in the 'markets' list in config.json. Exiting.")
            return

        # Assumption: historical_data.csv is for the *first* market in config['markets']
        first_market_symbol = traded_markets[0]
        historical_data_dict[first_market_symbol] = raw_data_df
        print(f"Assigning loaded CSV data to market: {first_market_symbol}")

        if len(traded_markets) > 1:
            print(f"Warning: Configuration lists multiple markets ({', '.join(traded_markets)}), "
                  f"but only data for the first market ({first_market_symbol}) is loaded from historical_data.csv.")
            # Future enhancement: Loop through markets and load respective data files if available.
            # For now, run_strategy will only operate on the data present in historical_data_dict.

        if not historical_data_dict: # Should be populated if traded_markets was not empty
            print("Error: historical_data_dict is empty. Cannot proceed. Exiting.")
            return

        # 4. Get Initial Capital
        # run_strategy expects initial_capital as an argument.
        # calculate_all_kpis will then get it from backtest_results['portfolio_summary'] or config.
        initial_capital = config.get('initial_capital', 1000000.0) # Default if not in config
        print(f"Initial capital set to: {initial_capital:,.2f}")

        # 5. Run Backtest
        print("Running strategy backtest...")
        # Ensure historical_data_dict values are DataFrames as expected by run_strategy's indicator calculations
        for market, df_market in historical_data_dict.items():
            if not isinstance(df_market, pd.DataFrame):
                print(f"Error: Data for market {market} is not a pandas DataFrame. Exiting.")
                return
            # Ensure necessary columns are present (run_strategy will also do checks, but good for early exit)
            expected_cols = ['Open', 'High', 'Low', 'Close']
            if not all(col in df_market.columns for col in expected_cols):
                print(f"Error: DataFrame for market {market} is missing one or more required columns: {expected_cols}. Exiting.")
                return


        backtest_results = trading_logic.run_strategy(historical_data_dict, initial_capital, config)
        if not backtest_results:
            print("Error: Backtest did not return results. Exiting.")
            return
        print("Backtest completed.")

        # 6. Calculate KPIs
        print("Calculating performance KPIs...")
        # risk_free_rate_annual can be taken from config if available, else defaults to 0.0 in calculate_all_kpis
        risk_free_rate = config.get('risk_free_rate_annual', 0.0)
        kpi_results = performance_analyzer.calculate_all_kpis(backtest_results, config, risk_free_rate_annual=risk_free_rate)
        if not kpi_results:
            print("Error: KPI calculation did not return results. Exiting.")
            return
        print("KPIs calculated.")

        # 7. Generate Report
        report_path = 'backtest_report.txt' # Output path for the report
        print(f"Generating text report at '{report_path}'...")
        performance_analyzer.generate_text_report(backtest_results, config, kpi_results, report_path)
        # generate_text_report already prints a success/error message.

        print("\nBacktest process finished.")

    except FileNotFoundError as e:
        print(f"Error: Required file not found: {e}. Please ensure config.json and historical_data.csv are present.")
    except KeyError as e:
        print(f"Error: Missing expected key in configuration or data: {e}.")
    except ValueError as e:
        print(f"Error: Value error encountered: {e}.")
    except Exception as e:
        print(f"An unexpected error occurred during the backtest process: {e}")
        # For debugging, you might want to print the full traceback
        # import traceback
        # traceback.print_exc()

if __name__ == '__main__':
    main()
