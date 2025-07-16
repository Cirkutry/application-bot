import json
import os
from typing import Any, Dict, List, Optional

APPLICATION_STORAGE_DIR = os.path.join(os.path.dirname(__file__), '../../storage/applications')

os.makedirs(APPLICATION_STORAGE_DIR, exist_ok=True)


class ApplicationDB:
    def _application_path(self, application_id: str) -> str:
        return os.path.join(APPLICATION_STORAGE_DIR, f"{application_id}.json")

    def save_application(self, application_id: str, data: Dict[str, Any]) -> None:
        with open(self._application_path(application_id), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load_application(self, application_id: str) -> Optional[Dict[str, Any]]:
        path = self._application_path(application_id)
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def delete_application(self, application_id: str) -> bool:
        path = self._application_path(application_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def list_applications(self) -> List[str]:
        return [fname[:-5] for fname in os.listdir(APPLICATION_STORAGE_DIR) if fname.endswith('.json')]


application_db = ApplicationDB()
