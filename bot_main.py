"""
Bot Trading Entry Point
Start the Marsia trading bot with spike detection strategy
"""

import sys
import logging
from config.settings import BotConfig
from bot import create_trading_bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for trading bot"""
    
    print("\n" + "="*80)
    print("MARSIA TRADING BOT - SPIKE DETECTION STRATEGY".center(80))
    print("="*80 + "\n")
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = BotConfig()
        
        # Validate configuration
        logger.info("Validating credentials...")
        BotConfig.validate()
        
        # Get Delta config
        delta_config = config.get_delta_config()
        
        # Create trading bot
        logger.info("Creating trading bot...")
        bot = create_trading_bot(
            api_config=delta_config,
            spike_percent=4.0,
            spike_bars=8,
            order_margin_usd=25.0,
            leverage=20.0,
            max_positions=5,
            poll_interval_sec=5.0
        )
        
        # Start bot
        logger.info("Starting trading bot...")
        bot.start()
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"\n✗ Configuration Error: {e}")
        print("\nPlease ensure:")
        print("  1. .env file exists (copy from .env.example)")
        print("  2. DELTA_API_KEY is set")
        print("  3. DELTA_API_SECRET is set")
        sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\n✓ Bot stopped gracefully")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n✗ Unexpected Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
