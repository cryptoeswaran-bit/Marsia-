"""
Main entry point for Marsia Trading Bot
Demonstrates API client usage and bot initialization
"""

import sys
import logging
from config.settings import BotConfig, get_bot_config
from api.delta_client import DeltaExchangeClient, DeltaWebSocketClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_header(text: str) -> None:
    """Print formatted header"""
    print("\n" + "="*80)
    print(text.center(80))
    print("="*80)


def print_subheader(text: str) -> None:
    """Print formatted subheader"""
    print("\n" + text)
    print("-" * len(text))


def main():
    """Main function - Initialize bot and run basic operations"""
    
    print_header("MARSIA TRADING BOT - INITIALIZATION")
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = BotConfig()
        
        # Validate configuration
        logger.info("Validating configuration...")
        BotConfig.validate()
        logger.info("✓ Configuration validated")
        
        # Display bot information
        print_subheader("Bot Information")
        print(f"Bot Name      : {config.API_NAME}")
        print(f"Mode          : {'Testnet (Testing)' if config.USE_TESTNET else 'Production'}")
        print(f"API URL       : {config.API_URL}")
        print(f"WebSocket URL : {config.WEBSOCKET_URL}")
        
        # Display trading configuration
        print_subheader("Trading Configuration")
        print(f"Default Symbol        : {config.DEFAULT_SYMBOL}")
        print(f"Default Quantity      : {config.DEFAULT_QUANTITY}")
        print(f"Max Position Size     : {config.MAX_POSITION_SIZE}")
        print(f"Stop Loss %            : {config.STOP_LOSS_PERCENTAGE}%")
        print(f"Take Profit %          : {config.TAKE_PROFIT_PERCENTAGE}%")
        print(f"Daily Loss Limit      : ${config.DAILY_LOSS_LIMIT}")
        print(f"Max Concurrent Orders : {config.MAX_CONCURRENT_ORDERS}")
        
        # Initialize Delta Exchange client
        logger.info("Initializing Delta Exchange API client...")
        delta_config = config.get_delta_config()
        client = DeltaExchangeClient(delta_config)
        
        print_subheader("API Client Initialization")
        print("✓ Delta Exchange API client initialized successfully")
        
        # Health check
        print_subheader("Step 1: Health Check")
        logger.info("Performing API health check...")
        if client.health_check():
            print("✓ API is accessible and healthy")
        else:
            print("✗ API health check failed")
            return
        
        # Display wallet balance
        print_subheader("Step 2: Wallet Balance")
        try:
            client.print_wallet_balance()
        except Exception as e:
            logger.error(f"Error fetching wallet balance: {e}")
            print(f"✗ Error: {e}")
        
        # Display perpetual futures
        print_subheader("Step 3: Available Perpetual Futures")
        try:
            client.print_perpetual_futures()
        except Exception as e:
            logger.error(f"Error fetching perpetual futures: {e}")
            print(f"✗ Error: {e}")
        
        # Display open positions
        print_subheader("Step 4: Open Positions")
        try:
            client.print_positions()
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            print(f"✗ Error: {e}")
        
        print_header("MARSIA BOT READY")
        print("\n✓ Bot successfully initialized and connected to Delta Exchange")
        print("\nNext Steps:")
        print("  1. Review your wallet balance and available funds")
        print("  2. Check current open positions")
        print("  3. Configure your trading strategies")
        print("  4. Set up risk management parameters")
        print("  5. Enable automated trading\n")
        
        # Optional: Start WebSocket (uncomment to enable)
        # print_subheader("Step 5: Starting Real-Time Data Stream")
        # logger.info("Initializing WebSocket client...")
        # ws_client = DeltaWebSocketClient(delta_config)
        # print("✓ WebSocket client initialized")
        # print("Starting real-time data stream...")
        # ws_client.start()
        
        # Close connection when done
        client.close_connection()
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"\n✗ Configuration Error: {e}")
        print("\nPlease ensure:")
        print("  1. .env file exists (copy from .env.example)")
        print("  2. DELTA_API_KEY is set")
        print("  3. DELTA_API_SECRET is set")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n✗ Unexpected Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
