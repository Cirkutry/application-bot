import json
import os
from typing import Any, Dict, List, Optional

POSITION_STORAGE_DIR = os.path.join(os.path.dirname(__file__), '../../storage/positions')

os.makedirs(POSITION_STORAGE_DIR, exist_ok=True)


class PositionDB:
    def _position_path(self, position_id: str) -> str:
        return os.path.join(POSITION_STORAGE_DIR, f"{position_id}.json")

    def save_position(self, position_id: str, data: Dict[str, Any]) -> None:
        with open(self._position_path(position_id), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load_position(self, position_id: str) -> Optional[Dict[str, Any]]:
        path = self._position_path(position_id)
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def delete_position(self, position_id: str) -> bool:
        path = self._position_path(position_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def list_positions(self) -> List[str]:
        return [fname[:-5] for fname in os.listdir(POSITION_STORAGE_DIR) if fname.endswith('.json')]


position_db = PositionDB()
