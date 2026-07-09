import json
from datetime import datetime, timezone
from hashlib import sha256

from factory import db


class TrainRecord(db.Model):
    __tablename__ = "train_records"

    id = db.Column(db.Integer, primary_key=True)
    source_table = db.Column(db.String(64), nullable=False, default="train", index=True)
    external_id = db.Column(db.String(128), nullable=True, index=True)
    payload_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    payload = db.Column(db.JSON, nullable=False)
    imported_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    @staticmethod
    def build_payload_hash(payload):
        normalized_payload = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
            separators=(",", ":"),
        )
        return sha256(normalized_payload.encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        return f"<TrainRecord {self.id} external_id={self.external_id}>"
