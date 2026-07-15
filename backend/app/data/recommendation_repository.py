from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.models import RecommendationSession, RecommendationSessionCreate


class RecommendationRepository:
    """本地单用户推荐会话仓库；只保存 Skill 已经生成的结果，不采集或伪造行情。"""

    _session_id_pattern = re.compile(r"^[a-zA-Z0-9_-]{8,80}$")

    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.latest_path = self.directory / "latest.json"

    def create(self, payload: RecommendationSessionCreate) -> RecommendationSession:
        session = RecommendationSession(
            **payload.model_dump(mode="json"),
            session_id=f"rec_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{uuid4().hex[:8]}",
            created_at=datetime.now(timezone.utc),
        )
        document = session.model_dump(mode="json")
        self._write_json(self.directory / f"{session.session_id}.json", document)
        self._write_json(self.latest_path, document)
        return session

    def get_latest(self) -> RecommendationSession | None:
        return self._read(self.latest_path)

    def get(self, session_id: str) -> RecommendationSession | None:
        if not self._session_id_pattern.fullmatch(session_id):
            return None
        return self._read(self.directory / f"{session_id}.json")

    @staticmethod
    def _write_json(path: Path, document: dict[str, object]) -> None:
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)

    @staticmethod
    def _read(path: Path) -> RecommendationSession | None:
        try:
            return RecommendationSession.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
