"""Simple JSON-based user data storage."""

import json
import os
from typing import Set, Optional
from threading import Lock


class UserDataManager:
    def __init__(self, filepath: str = "user_data.json"):
        self.filepath = filepath
        self.lock = Lock()
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create the JSON file if it doesn't exist."""
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w') as f:
                json.dump({}, f)
    
    def _load_data(self) -> dict:
        """Load all user data from JSON file."""
        with open(self.filepath, 'r') as f:
            return json.load(f)
    
    def _save_data(self, data: dict):
        """Save all user data to JSON file."""
        with open(self.filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_user_data(self, user_id: int) -> dict:
        """Get all data for a specific user."""
        with self.lock:
            data = self._load_data()
            user_key = str(user_id)
            return data.get(user_key, {
                "pincode": None,
                "selected_products": []
            })
    
    def set_pincode(self, user_id: int, pincode: str):
        """Set user's pincode."""
        with self.lock:
            data = self._load_data()
            user_key = str(user_id)
            
            if user_key not in data:
                data[user_key] = {"pincode": None, "selected_products": []}
            
            data[user_key]["pincode"] = pincode
            self._save_data(data)
    
    def get_pincode(self, user_id: int) -> Optional[str]:
        """Get user's pincode."""
        return self.get_user_data(user_id).get("pincode")
    
    def set_selected_products(self, user_id: int, products: Set[str]):
        """Set user's selected products."""
        with self.lock:
            data = self._load_data()
            user_key = str(user_id)
            
            if user_key not in data:
                data[user_key] = {"pincode": None, "selected_products": []}
            
            data[user_key]["selected_products"] = list(products)
            self._save_data(data)
    
    def get_selected_products(self, user_id: int) -> Set[str]:
        """Get user's selected products."""
        products = self.get_user_data(user_id).get("selected_products", [])
        return set(products)
    
    def clear_user(self, user_id: int):
        """Remove all data for a user."""
        with self.lock:
            data = self._load_data()
            user_key = str(user_id)
            
            if user_key in data:
                del data[user_key]
                self._save_data(data)
    
    def get_all_users(self) -> list:
        """Get list of all user IDs."""
        with self.lock:
            data = self._load_data()
            return [int(uid) for uid in data.keys()]
