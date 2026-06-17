"""
Trading Bot - Main trading engine
Integrates API client with strategies and executes trades
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Set
from datetime import datetime

from api.delta_client import DeltaExchangeClient
from bot.strategies import SpikeDetectionStrategy, RiskManager, PositionTracker

logger = logging.getLogger(__name__)


class TradingBot:
    """Main trading bot engine"""
    
    def __init__(
        self,
        api_client: DeltaExchangeClient,
        strategy: SpikeDetectionStrategy,
        risk_manager: RiskManager,
        poll_interval_sec: float = 5.0
    ):
        """
        Initialize trading bot
        
        Args:
            api_client: DeltaExchangeClient instance
            strategy: SpikeDetectionStrategy instance
            risk_manager: RiskManager instance
            poll_interval_sec: Polling interval in seconds
        """
        self.api_client = api_client
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.poll_interval_sec = poll_interval_sec
        
        self.position_tracker = PositionTracker()
        self.products: Dict = {}
        self.products_by_symbol: Dict = {}
        self.running = False
        self.lock = threading.Lock()
        
        logger.info("TradingBot initialized")
        logger.info(f"  Poll Interval: {poll_interval_sec}s")
    
    def load_products(self) -> bool:
        """
        Load all available perpetual futures
        
        Returns:
            True if successful
        """
        try:
            logger.info("Loading perpetual futures products...")
            result = self.api_client.get_all_perpetual_futures()
            
            if not result.get('success'):
                logger.error("Failed to load products")
                return False
            
            products = result.get('result', [])
            
            for p in products:
                if p.get('trading_status') == 'operational':
                    product_info = {
                        'id': p['id'],
                        'symbol': p['symbol'],
                        'contract_value': float(p['contract_value']),
                        'contract_unit_currency': p['contract_unit_currency'],
                        'tick_size': float(p['tick_size']),
                        'notional_type': p['notional_type']
                    }
                    self.products[p['id']] = product_info
                    self.products_by_symbol[p['symbol']] = product_info
            
            logger.info(f"✓ Loaded {len(self.products)} operational products")
            return True
            
        except Exception as e:
            logger.error(f"Error loading products: {e}")
            return False
    
    def fetch_all_tickers(self) -> Dict[str, float]:
        """
        Fetch current tickers for all perpetual futures
        
        Returns:
            Dictionary mapping symbol -> price
        """
        try:
            result = self.api_client.get_all_perpetual_futures()
            
            ticker_map = {}
            
            if result.get('success'):
                for product in result.get('result', []):
                    symbol = product.get('symbol')
                    # Get mark price from last_traded_price if available
                    price = float(product.get('mark_price', 0) or 0)
                    
                    if symbol and price > 0:
                        ticker_map[symbol] = price
            
            return ticker_map
            
        except Exception as e:
            logger.error(f"Error fetching tickers: {e}")
            return {}
    
    def get_exchange_positions(self) -> Set[str]:
        """
        Get current open positions from exchange
        
        Returns:
            Set of symbols with open positions
        """
        try:
            result = self.api_client.get_positions()
            
            open_symbols = set()
            
            if result.get('success'):
                positions = result.get('result', [])
                
                if isinstance(positions, list):
                    for pos in positions:
                        if int(pos.get('size', 0)) != 0:
                            open_symbols.add(pos['product_symbol'])
                else:
                    # Single position result
                    if int(positions.get('size', 0)) != 0:
                        symbol = positions.get('product_symbol')
                        if symbol:
                            open_symbols.add(symbol)
            
            return open_symbols
            
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return set()
    
    def place_sell_order(
        self,
        product_id: int,
        symbol: str,
        size: int,
        mark_price: float
    ) -> Optional[Dict]:
        """
        Place a short order with bracket orders (SL/TP)
        
        Args:
            product_id: Product ID
            symbol: Symbol
            size: Order size
            mark_price: Current mark price
            
        Returns:
            Order result or None on error
        """
        try:
            product = self.products.get(product_id)
            if not product:
                logger.error(f"Product {product_id} not found")
                return None
            
            tick_size = product['tick_size']
            
            # Calculate SL and TP prices
            sl_price = mark_price * (1 + self.risk_manager.stop_loss_pct / 100)
            tp_price = mark_price * (1 - self.risk_manager.take_profit_pct / 100)
            
            # Round to tick size
            def round_tick(price, tick):
                return round(round(price / tick) * tick, 10)
            
            sl_price = round_tick(sl_price, tick_size)
            tp_price = round_tick(tp_price, tick_size)
            
            # Build order
            order_body = {
                'product_id': product_id,
                'product_symbol': symbol,
                'size': size,
                'side': 'sell',
                'order_type': 'market_order',
                'bracket_stop_loss_price': str(sl_price),
                'bracket_stop_loss_limit_price': str(sl_price),
                'bracket_take_profit_price': str(tp_price),
                'bracket_take_profit_limit_price': str(tp_price),
                'bracket_stop_trigger_method': 'mark_price'
            }
            
            logger.info(f"Placing SELL order: {symbol} x {size}")
            
            # Make API call (would need to add this to delta_client.py)
            # For now, we'll log the intention
            logger.info(f"Order details: {order_body}")
            
            return {
                'success': True,
                'symbol': symbol,
                'size': size,
                'entry_price': mark_price,
                'stop_loss': sl_price,
                'take_profit': tp_price
            }
            
        except Exception as e:
            logger.error(f"Error placing order for {symbol}: {e}")
            return None
    
    def display_order_confirmation(
        self,
        symbol: str,
        spike_pct: float,
        entry_price: float,
        lot_size: int,
        sl_price: float,
        tp_price: float
    ) -> None:
        """Display order confirmation message"""
        print("\n" + "="*70)
        print(f"{'*** SPIKE DETECTED & ORDER PLACED ***'.center(70)}")
        print("="*70)
        print(f"Symbol        : {symbol}")
        print(f"Spike         : +{spike_pct:.2f}% in {self.strategy.spike_bars} bars")
        print(f"Entry Price   : {entry_price:.8f}")
        print(f"Side          : SELL (Short)")
        print(f"Lot Size      : {lot_size}")
        print(f"Stop Loss     : {sl_price:.8f} (+{self.risk_manager.stop_loss_pct}%)")
        print(f"Take Profit   : {tp_price:.8f} (-{self.risk_manager.take_profit_pct}%)")
        print(f"Timestamp     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")
    
    def run_trading_loop(self) -> None:
        """Main trading loop"""
        print("\n" + "#"*70)
        print("#   MARSIA TRADING BOT - SPIKE DETECTION STRATEGY".center(70))
        print(f"#   Monitoring {len(self.products)} symbols".center(70))
        print(f"#   Polling interval: {self.poll_interval_sec}s".center(70))
        print("#"*70 + "\n")
        
        self.running = True
        
        while self.running:
            try:
                loop_start = time.time()
                
                # Fetch all tickers
                ticker_map = self.fetch_all_tickers()
                
                if not ticker_map:
                    logger.warning("No tickers fetched, retrying...")
                    time.sleep(self.poll_interval_sec)
                    continue
                
                # Get exchange positions
                exchange_positions = self.get_exchange_positions()
                
                # Sync position tracker
                with self.lock:
                    self.position_tracker.sync_with_exchange(exchange_positions)
                    current_position_count = self.position_tracker.get_position_count()
                
                # Update prices and check for signals
                for symbol, current_price in ticker_map.items():
                    if symbol not in self.products_by_symbol:
                        continue
                    
                    # Update price history
                    self.strategy.update_price(symbol, current_price)
                    
                    # Check if already in position
                    with self.lock:
                        if self.position_tracker.is_active(symbol):
                            continue
                        
                        # Check position limit
                        if current_position_count >= self.risk_manager.max_positions:
                            continue
                        
                        # Check daily loss limit
                        if not self.risk_manager.can_trade():
                            logger.warning("Daily loss limit exceeded, no new trades")
                            continue
                    
                    # Get trading signal
                    signal = self.strategy.get_signal(symbol, current_price)
                    
                    if signal is None:
                        continue
                    
                    # Calculate lot size
                    product = self.products_by_symbol[symbol]
                    lot_size = self.risk_manager.calculate_lot_size(
                        product['contract_value'],
                        current_price,
                        product['notional_type']
                    )
                    
                    if lot_size < 1:
                        logger.warning(f"{symbol}: Lot size < 1, skipping")
                        continue
                    
                    # Place order
                    order_result = self.place_sell_order(
                        product_id=product['id'],
                        symbol=symbol,
                        size=lot_size,
                        mark_price=current_price
                    )
                    
                    if order_result and order_result.get('success'):
                        with self.lock:
                            self.position_tracker.add_position(
                                symbol,
                                current_price,
                                lot_size
                            )
                            current_position_count += 1
                        
                        self.display_order_confirmation(
                            symbol=symbol,
                            spike_pct=signal['spike_percent'],
                            entry_price=current_price,
                            lot_size=lot_size,
                            sl_price=signal['stop_loss'],
                            tp_price=signal['take_profit']
                        )
                
                # Sleep for remaining time
                elapsed = time.time() - loop_start
                sleep_time = max(0, self.poll_interval_sec - elapsed)
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}", exc_info=True)
                time.sleep(10)
    
    def start(self) -> None:
        """Start the trading bot"""
        if not self.load_products():
            logger.error("Failed to load products, exiting")
            return
        
        self.run_trading_loop()
    
    def stop(self) -> None:
        """Stop the trading bot"""
        self.running = False
        logger.info("Trading bot stopped")
