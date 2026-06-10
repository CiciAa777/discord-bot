from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Note:
    user_id: str
    content_text: str
    source_type: str          # "image" | "text"
    image_path: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    id: Optional[int] = None  # set after DB insert
    ocr_failed: bool = False
    is_sensitive: bool = False
    discord_message_id: Optional[str] = None