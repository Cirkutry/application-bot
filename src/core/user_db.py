import json
import os
from typing import Any, Dict, List, Optional

USER_STORAGE_DIR = os.path.join(os.path.dirname(__file__), '../../storage/users')

os.makedirs(USER_STORAGE_DIR, exist_ok=True)


class UserDB:
    def _user_path(self, user_id: str) -> str:
        return os.path.join(USER_STORAGE_DIR, f"{user_id}.json")

    def save_user(self, user_id: str, data: Dict[str, Any]) -> None:
        with open(self._user_path(user_id), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        path = self._user_path(user_id)
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def delete_user(self, user_id: str) -> bool:
        path = self._user_path(user_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def list_users(self) -> List[str]:
        return [fname[:-5] for fname in os.listdir(USER_STORAGE_DIR) if fname.endswith('.json')]


user_db = UserDB()
