import pandas as pd
import data_loader
import config_loader
import trading_logic # Specifically run_strategy
import performance_analyzer # Specifically calculate_all_kpis, generate_text_report
from logger import setup_logging, get_logger

# Logger will be configured in main() after loading config.
# For now, a placeholder if any top-level logging is needed before that (unlikely for this script).
# main_logger = get_logger(__name__) # Placeholder, will be re-assigned in main

def main():
    """
    Main function to run the backtesting process.
    """
    # Initial log to console, file logging will start after config is loaded.
    # print("Attempting to start backtest process...") # Temporary, will be replaced by logger

    try:
        # 1. Load Configuration
        # print("Loading configuration...") # Replaced by logger after setup
        config = config_loader.load_config('config.json')
        if not config:
            # Logging setup might not have happened if config load failed.
            # Fallback to print or a default logger if essential.
            print("Error: Configuration file could not be loaded. Exiting.") # Keep print if logger fails
            # If logger.py is robust, it might log to console even if file setup fails.
            # For now, assume config_loader's logger handled the specific error.
            return

        # Setup Logging as early as possible after config is loaded
        logging_config = config.get('logging', {})
        default_log_path = "trading_system.log"
        default_log_level = "INFO"

        log_file_path = logging_config.get('log_file_path', default_log_path)
        log_level = logging_config.get('log_level', default_log_level)

        if not logging_config or 'log_file_path' not in logging_config or 'log_level' not in logging_config:
            # Using print here as logger might not be fully set up, or to ensure this message goes to console.
            print(f"Warning: Logging configuration missing or incomplete in config.json. Using defaults: path='{log_file_path}', level='{log_level}'.")

        setup_logging(log_file_path, log_level)
        main_logger = get_logger(__name__) # Now properly initialized

        main_logger.debug("Test DEBUG message: main_backtest main_logger initialized.") # For testing log levels
        main_logger.info("Starting backtest process...")
        main_logger.info("Loading configuration...") # Log again, now that proper logger is set up
        main_logger.info(f"Configuration loaded: {config}") # Consider logging a summary or specific keys

        # 2. Load Historical Data
        main_logger.info("Loading historical data...")
        raw_data_df = data_loader.load_csv_data('historical_data.csv')
        if raw_data_df.empty:
            main_logger.error("Error: Historical data file could not be loaded or is empty. Exiting.")
            return

        if 'Timestamp' not in raw_data_df.columns:
            main_logger.error("Error: 'Timestamp' column not found in historical_data.csv. Exiting.")
            return

        try:
            raw_data_df['Timestamp'] = pd.to_datetime(raw_data_df['Timestamp'])
        except Exception as e:
            main_logger.error(f"Error converting 'Timestamp' column to datetime: {e}. Exiting.")
            return

        raw_data_df.set_index('Timestamp', inplace=True)
        # Log after successful loading and processing:
        # This message was requested but needs first_market_symbol, defined later.
        # main_logger.info(f"Historical data loaded for {first_market_symbol} with {len(raw_data_df)} rows.") - Will add later

        # 3. Prepare historical_data_dict
        main_logger.info("Preparing historical data dictionary...")
        historical_data_dict = {}
        traded_markets = config.get('markets', [])

        if not traded_markets:
            main_logger.error("Error: No markets specified in the 'markets' list in config.json. Exiting.")
            return

        first_market_symbol = traded_markets[0]
        historical_data_dict[first_market_symbol] = raw_data_df
        main_logger.info(f"Assigning loaded CSV data to market: {first_market_symbol}")
        main_logger.info(f"Historical data loaded for {first_market_symbol} with {len(raw_data_df)} rows.")


        if len(traded_markets) > 1:
            main_logger.warning(f"Configuration lists multiple markets ({', '.join(traded_markets)}), "
                                f"but only data for the first market ({first_market_symbol}) is loaded from historical_data.csv.")

        if not historical_data_dict:
            main_logger.error("Error: historical_data_dict is empty. Cannot proceed. Exiting.")
            return

        # 4. Get Initial Capital
        initial_capital = config.get('initial_capital', 1000000.0)
        main_logger.info(f"Initial capital set to: {initial_capital:,.2f}")

        # Retrieve emergency_stop flag
        emergency_stop_enabled = config.get('emergency_stop', False)
        if emergency_stop_enabled:
            main_logger.warning("EMERGENCY STOP ACTIVATED: New trade entries will be disabled.")
        else:
            main_logger.info("Emergency stop is not activated. System operating normally.")

        # 5. Run Backtest
        main_logger.info("Running strategy backtest...")
        for market, df_market in historical_data_dict.items():
            if not isinstance(df_market, pd.DataFrame):
                main_logger.error(f"Error: Data for market {market} is not a pandas DataFrame. Exiting.")
                return
            expected_cols = ['Open', 'High', 'Low', 'Close']
            if not all(col in df_market.columns for col in expected_cols):
                main_logger.error(f"Error: DataFrame for market {market} is missing one or more required columns: {expected_cols}. Exiting.")
                return

        backtest_results = trading_logic.run_strategy(
            historical_data_dict,
            initial_capital,
            config,
            emergency_stop_activated=emergency_stop_enabled
        )
        if not backtest_results: # trading_logic.run_strategy should log its own errors if it returns None/empty
            main_logger.error("Error: Backtest did not return results. Exiting.")
            return
        main_logger.info("Backtest completed.")

        # 6. Calculate KPIs
        main_logger.info("Calculating performance KPIs...")
        risk_free_rate = config.get('risk_free_rate_annual', 0.0)
        kpi_results = performance_analyzer.calculate_all_kpis(backtest_results, config, risk_free_rate_annual=risk_free_rate)
        if not kpi_results:
            main_logger.error("Error: KPI calculation did not return results. Exiting.")
            return
        main_logger.info("KPIs calculated.")

        # 7. Generate Report
        report_path = 'backtest_report.txt'
        main_logger.info(f"Generating text report at '{report_path}'...")
        performance_analyzer.generate_text_report(backtest_results, config, kpi_results, report_path)
        # generate_text_report should ideally log its own success/failure.
        # If it doesn't, we can add: main_logger.info(f"Text report generated at '{report_path}'.")

        main_logger.info("Backtest process finished.")

    except FileNotFoundError as e:
        # Logger might not be initialized if config.json was the missing file
        if 'main_logger' in locals():
            main_logger.error(f"Error: Required file not found: {e}. Please ensure config.json and historical_data.csv are present.")
        else:
            print(f"Critical Error: Required file not found before logger initialization: {e}.")
    except KeyError as e:
        if 'main_logger' in locals():
            main_logger.error(f"Error: Missing expected key in configuration or data: {e}.")
        else:
            print(f"Critical Error: Missing key before logger initialization: {e}.")
    except ValueError as e:
        if 'main_logger' in locals():
            main_logger.error(f"Error: Value error encountered: {e}.")
        else:
            print(f"Critical Error: Value error before logger initialization: {e}.")
    except Exception as e:
        if 'main_logger' in locals():
            main_logger.exception(f"An unexpected error occurred during the backtest process: {e}")
        else:
            print(f"Critical Error: An unexpected error occurred before logger initialization: {e}")
            # import traceback # Keep for pre-logger critical errors
            # traceback.print_exc()

if __name__ == '__main__':
    main()
