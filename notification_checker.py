"""Background task to check product availability and send notifications."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List, Set

import requests

from api_client import AmulAPIClient
from config import Config
from user_data_manager import UserDataManager  # Changed from UserStateManager

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class NotificationChecker:
    """Background checker for product availability."""
    
    def __init__(self, check_interval: int = 300):
        """
        Initialize the checker.
        
        Args:
            check_interval: Time between checks in seconds (default: 5 minutes)
        """
        self.check_interval = check_interval
        self.user_data = UserDataManager()  # Use JSON-based manager
        self.last_notified: Dict[int, Dict[str, float]] = {}  # Track notifications in memory
    
    async def send_telegram_notification(
        self, 
        user_id: int, 
        message: str
    ) -> bool:
        """Send notification to a specific user."""
        if not Config.TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN not set")
            return False
        
        url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
        
        payload = {
            "chat_id": user_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            
            if response.ok:
                logger.info(f"Notification sent to user {user_id}")
                return True
            else:
                logger.error(f"Telegram API error for user {user_id}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send notification to user {user_id}: {e}")
            return False
    
    def should_notify(self, user_id: int, product_alias: str, cooldown_hours: int = 24) -> bool:
        """Check if enough time has passed since last notification for this product."""
        if user_id not in self.last_notified:
            return True
        
        if product_alias not in self.last_notified[user_id]:
            return True
        
        last_time = self.last_notified[user_id][product_alias]
        current_time = time.time()
        hours_passed = (current_time - last_time) / 3600
        
        return hours_passed >= cooldown_hours
    
    def mark_notified(self, user_id: int, product_alias: str):
        """Mark that we've notified the user about this product."""
        if user_id not in self.last_notified:
            self.last_notified[user_id] = {}
        
        self.last_notified[user_id][product_alias] = time.time()
    
    def check_user_products(self, user_id: int) -> tuple[List[Dict], List[Dict]]:
        """Check availability for a specific user's products.
        
        Returns:
            Tuple of (newly_available, all_available)
        """
        # Get user data from JSON
        user_data = self.user_data.get_user_data(user_id)
        
        pincode = user_data.get("pincode")
        selected_products = set(user_data.get("selected_products", []))
        
        if not pincode or not selected_products:
            logger.debug(f"User {user_id} has no pincode or products configured")
            return [], []
        
        try:
            # Create API client and fetch products
            logger.info(f"Checking products for user {user_id} with pincode {pincode}")
            
            temp_client = AmulAPIClient()
            temp_client.set_store_preferences(pincode)
            all_products = temp_client.get_products()
            
            # Find all available products and newly available ones
            newly_available = []
            all_available = []
            
            for product in all_products:
                alias = product.get("alias")
                
                if alias not in selected_products:
                    continue
                
                is_available = product.get("available", 0) > 0
                
                if is_available:
                    all_available.append(product)
                    
                    # Check if this is newly available (not notified in last 24h)
                    if self.should_notify(user_id, alias, cooldown_hours=24):
                        newly_available.append(product)
            
            # Mark all available products as notified
            for product in newly_available:
                self.mark_notified(user_id, product.get("alias"))
            
            # Clean up - suppress warnings
            try:
                temp_client.driver.quit()
            except Exception:
                pass  # Ignore cleanup errors
            
            return newly_available, all_available
            
        except Exception as e:
            logger.error(f"Error checking products for user {user_id}: {e}")
            return [], []
    
    async def check_all_users(self) -> None:
        """Check products for all users and send notifications."""
        user_ids = self.user_data.get_all_users()
        
        if not user_ids:
            logger.info("No users to check")
            return
        
        logger.info(f"Checking products for {len(user_ids)} users")
        
        for user_id in user_ids:
            try:
                newly_available, all_available = self.check_user_products(user_id)
                
                # Send notification showing all available products
                if all_available:
                    message = self._format_notification_message(all_available, newly_available)
                    await self.send_telegram_notification(user_id, message)
                    logger.info(f"Notified user {user_id} - {len(all_available)} available ({len(newly_available)} new)")
                else:
                    logger.debug(f"No products available for user {user_id}")
                
                # Small delay between users to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing user {user_id}: {e}")
                continue
    
    def _format_notification_message(self, all_available: List[Dict], newly_available: List[Dict]) -> str:
        """Format products into a notification message."""
        new_count = len(newly_available)
        total_count = len(all_available)
        
        if new_count > 0:
            message = f"🎉 *{new_count} New Product(s) Available!*\n\n"
        else:
            message = f"📦 *Product Availability Update*\n\n"
        
        message += f"Total available: {total_count} product(s)\n\n"
        
        # Mark newly available products with 🆕
        newly_available_aliases = {p.get("alias") for p in newly_available}
        
        for product in all_available:
            name = product.get("name", "Unknown")
            price = product.get("price", 0)
            alias = product.get("alias", "")
            stock = product.get("inventory_quantity", 0)
            url = f"https://shop.amul.com/en/product/{alias}"
            
            # Mark new products
            new_badge = "🆕 " if alias in newly_available_aliases else ""
            
            message += f"{new_badge}• *{name}*\n"
            message += f"  💰 Price: ₹{price}\n"
            message += f"  📦 Stock Available: *{stock}*\n"
            message += f"  🔗 [View Product]({url})\n\n"
        
        message += "Order now before it's out of stock! 🏃‍♂️"
        
        return message
    
    async def run_forever(self) -> None:
        """Run the checker continuously."""
        logger.info(f"🔔 Starting notification checker (interval: {self.check_interval}s)")
        
        while True:
            try:
                start_time = time.time()
                
                await self.check_all_users()
                
                elapsed = time.time() - start_time
                logger.info(f"✅ Check completed in {elapsed:.2f} seconds")
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Checker stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in checker loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    def run(self) -> None:
        """Run the checker (blocking)."""
        asyncio.run(self.run_forever())


def main():
    """Main entry point for the notification checker."""
    import os
    
    # Check interval from environment or default to 5 minutes
    check_interval = int(os.getenv("CHECK_INTERVAL", "300"))
    
    logger.info(f"🚀 Starting Amul Product Notification Checker")
    logger.info(f"⏱️  Check interval: {check_interval} seconds ({check_interval//60} minutes)")
    
    checker = NotificationChecker(check_interval=check_interval)
    checker.run()


if __name__ == "__main__":
    main()
