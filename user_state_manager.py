"""User state management with Redis."""

from __future__ import annotations

import json
import logging
from typing import Optional, Set

import redis

from config import Config

logger = logging.getLogger(__name__)


class UserStateManager:
    """Manage per-user state in Redis."""
    
    def __init__(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=Config.REDIS_DB,
                password=Config.REDIS_PASSWORD,
                decode_responses=True,
                ssl=Config.REDIS_SSL,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            self.redis_client.ping()
            logger.info("Connected to Redis for user state management")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Fallback to in-memory storage
            self.redis_client = None
            self._memory_storage = {}
            logger.warning("Using in-memory storage as fallback")
    
    def _get_key(self, user_id: int, key_type: str) -> str:
        """Generate Redis key for user data."""
        return f"{Config.REDIS_KEY_PREFIX}user:{user_id}:{key_type}"
    
    def set_pincode(self, user_id: int, pincode: str) -> bool:
        """Set user's pincode."""
        key = self._get_key(user_id, "pincode")
        
        try:
            if self.redis_client:
                self.redis_client.set(key, pincode)
                self.redis_client.expire(key, 30 * 24 * 60 * 60)  # 30 days
            else:
                self._memory_storage[key] = pincode
            
            logger.info(f"Set pincode for user {user_id}: {pincode}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting pincode for user {user_id}: {e}")
            return False
    
    def get_pincode(self, user_id: int) -> Optional[str]:
        """Get user's pincode."""
        key = self._get_key(user_id, "pincode")
        
        try:
            if self.redis_client:
                return self.redis_client.get(key)
            else:
                return self._memory_storage.get(key)
                
        except Exception as e:
            logger.error(f"Error getting pincode for user {user_id}: {e}")
            return None
    
    def set_selected_products(self, user_id: int, product_aliases: Set[str]) -> bool:
        """Set user's selected products."""
        key = self._get_key(user_id, "products")
        
        try:
            if self.redis_client:
                self.redis_client.delete(key)
                if product_aliases:
                    self.redis_client.sadd(key, *product_aliases)
                self.redis_client.expire(key, 30 * 24 * 60 * 60)  # 30 days
            else:
                self._memory_storage[key] = product_aliases
            
            logger.info(f"Set {len(product_aliases)} products for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting products for user {user_id}: {e}")
            return False
    
    def get_selected_products(self, user_id: int) -> Set[str]:
        """Get user's selected products."""
        key = self._get_key(user_id, "products")
        
        try:
            if self.redis_client:
                result = self.redis_client.smembers(key)
                return set(result) if result else set()
            else:
                return self._memory_storage.get(key, set())
                
        except Exception as e:
            logger.error(f"Error getting products for user {user_id}: {e}")
            return set()
    
    def add_product(self, user_id: int, product_alias: str) -> bool:
        """Add a product to user's tracking list."""
        key = self._get_key(user_id, "products")
        
        try:
            if self.redis_client:
                self.redis_client.sadd(key, product_alias)
                self.redis_client.expire(key, 30 * 24 * 60 * 60)
            else:
                if key not in self._memory_storage:
                    self._memory_storage[key] = set()
                self._memory_storage[key].add(product_alias)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding product for user {user_id}: {e}")
            return False
    
    def remove_product(self, user_id: int, product_alias: str) -> bool:
        """Remove a product from user's tracking list."""
        key = self._get_key(user_id, "products")
        
        try:
            if self.redis_client:
                self.redis_client.srem(key, product_alias)
            else:
                if key in self._memory_storage:
                    self._memory_storage[key].discard(product_alias)
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing product for user {user_id}: {e}")
            return False
    
    def get_all_users(self) -> Set[int]:
        """Get all user IDs with active tracking."""
        try:
            if self.redis_client:
                pattern = f"{Config.REDIS_KEY_PREFIX}user:*:pincode"
                keys = self.redis_client.keys(pattern)
                
                user_ids = set()
                for key in keys:
                    # Extract user_id from key: prefix:user:USER_ID:pincode
                    parts = key.split(":")
                    if len(parts) >= 3:
                        try:
                            user_id = int(parts[2])
                            user_ids.add(user_id)
                        except ValueError:
                            continue
                
                return user_ids
            else:
                # Extract from memory storage
                user_ids = set()
                for key in self._memory_storage.keys():
                    if ":pincode" in key:
                        parts = key.split(":")
                        if len(parts) >= 3:
                            try:
                                user_id = int(parts[2])
                                user_ids.add(user_id)
                            except ValueError:
                                continue
                return user_ids
                
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return set()
    
    def get_user_data(self, user_id: int) -> dict:
        """Get all data for a user."""
        return {
            "pincode": self.get_pincode(user_id),
            "products": self.get_selected_products(user_id),
        }
    
    def clear_user(self, user_id: int) -> bool:
        """Clear all data for a user."""
        try:
            pincode_key = self._get_key(user_id, "pincode")
            products_key = self._get_key(user_id, "products")
            
            if self.redis_client:
                self.redis_client.delete(pincode_key, products_key)
            else:
                self._memory_storage.pop(pincode_key, None)
                self._memory_storage.pop(products_key, None)
            
            logger.info(f"Cleared data for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing data for user {user_id}: {e}")
            return False
    
    def set_last_notification(self, user_id: int, product_alias: str) -> bool:
        """Record when a notification was sent for a product."""
        key = self._get_key(user_id, f"notified:{product_alias}")
        
        try:
            if self.redis_client:
                import time
                self.redis_client.set(key, str(time.time()))
                self.redis_client.expire(key, 1 * 60)  #10 min
            else:
                import time
                self._memory_storage[key] = str(time.time())
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting notification time: {e}")
            return False
    
    def should_notify(self, user_id: int, product_alias: str, cooldown_hours: int = 24) -> bool:
        """Check if enough time has passed since last notification."""
        key = self._get_key(user_id, f"notified:{product_alias}")
        
        try:
            if self.redis_client:
                last_time = self.redis_client.get(key)
            else:
                last_time = self._memory_storage.get(key)
            
            if not last_time:
                return True
            
            import time
            elapsed_hours = (time.time() - float(last_time)) / 3600
            return elapsed_hours >= cooldown_hours
            
        except Exception as e:
            logger.error(f"Error checking notification time: {e}")
            return True  # On error, allow notification
