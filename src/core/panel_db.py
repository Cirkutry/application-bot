import json
import os
from typing import Any, Dict, List, Optional

PANEL_STORAGE_DIR = os.path.join(os.path.dirname(__file__), '../../storage/panels')

os.makedirs(PANEL_STORAGE_DIR, exist_ok=True)


class PanelDB:
    def _panel_path(self, panel_id: str) -> str:
        return os.path.join(PANEL_STORAGE_DIR, f"{panel_id}.json")

    def save_panel(self, panel_id: str, data: Dict[str, Any]) -> None:
        with open(self._panel_path(panel_id), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load_panel(self, panel_id: str) -> Optional[Dict[str, Any]]:
        path = self._panel_path(panel_id)
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def delete_panel(self, panel_id: str) -> bool:
        path = self._panel_path(panel_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def list_panels(self) -> List[str]:
        return [fname[:-5] for fname in os.listdir(PANEL_STORAGE_DIR) if fname.endswith('.json')]


panel_db = PanelDB()
