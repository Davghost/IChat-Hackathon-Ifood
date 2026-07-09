from datetime import datetime, timezone

from supabase import create_client

from factory import db
from main import app
from models.train_record import TrainRecord
import os
from dotenv import load_dotenv

load_dotenv()

URL = os.environ.get('URL')
KEY = os.environ.get('KEY')

supabase = create_client(URL, KEY)
SOURCE_TABLE = "train"


def get_orders():
    response = (
        supabase
        .table(SOURCE_TABLE)
        .select("*")
        .execute()
    )

    return response.data


def sync_train_orders():
    records = get_orders()
    inserted = 0
    skipped = 0

    with app.app_context():
        for payload in records:
            payload_hash = TrainRecord.build_payload_hash(payload)
            existing_record = TrainRecord.query.filter_by(payload_hash=payload_hash).first()
            if existing_record:
                skipped += 1
                continue

            external_id = payload.get("id")
            train_record = TrainRecord(
                source_table=SOURCE_TABLE,
                external_id=str(external_id) if external_id is not None else None,
                payload_hash=payload_hash,
                payload=payload,
                imported_at=datetime.now(timezone.utc),
            )
            db.session.add(train_record)
            inserted += 1

        db.session.commit()

    return {
        "fetched": len(records),
        "inserted": inserted,
        "skipped": skipped,
    }


if __name__ == "__main__":
    result = sync_train_orders()
    print(
        "Sync complete: "
        f"fetched={result['fetched']} inserted={result['inserted']} skipped={result['skipped']}"
    )
