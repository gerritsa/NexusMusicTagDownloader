from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class Track:
    file_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    dirty: bool = False # Has unsaved changes

    @property
    def filename(self) -> str:
        import os
        return os.path.basename(self.file_path)
