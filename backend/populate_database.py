import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from factory import db
from main import app
from models.menu_item import MenuItem
from models.train_record import TrainRecord
from models.user import User
from sqlalchemy import select


DEFAULT_OWNER_EMAIL = "owner@hackathon.local"
DEFAULT_OWNER_USERNAME = "owner"
DEFAULT_OWNER_PASSWORD = "owner123"

DELIVERIES_SOURCE_TABLE = "train"
DEMAND_SOURCE_TABLE = "demand_daily"
OWNER_ORDERS_SOURCE_TABLE = "owner_orders"
SEED_SOURCE_TABLES = (DELIVERIES_SOURCE_TABLE, DEMAND_SOURCE_TABLE, "test")

BASE_DIR = Path(__file__).resolve().parent
DATASETS_DIR = BASE_DIR.parent / "datasets"
DELIVERIES_CSV = DATASETS_DIR / "deliveries_train.csv"
DEMAND_CSV = DATASETS_DIR / "demand_daily_train.csv"
MENU_ITEM_LIMIT = 12


def read_csv_rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def parse_iso_datetime(value: str) -> str:
    parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return parsed.isoformat()


def parse_number(value, caster=float, default=0):
    if value in (None, ""):
        return default
    return caster(value)


def ensure_owner():
    owner = db.session.scalars(
        select(User).filter_by(email=DEFAULT_OWNER_EMAIL)
    ).first()

    if owner is None:
        owner = User(
            username=DEFAULT_OWNER_USERNAME,
            email=DEFAULT_OWNER_EMAIL,
            role="owner",
        )
        db.session.add(owner)

    owner.username = DEFAULT_OWNER_USERNAME
    owner.role = "owner"
    owner.password = DEFAULT_OWNER_PASSWORD
    db.session.flush()
    return owner


def reset_seed_train_records():
    deleted = (
        TrainRecord.query
        .filter(TrainRecord.source_table.in_(SEED_SOURCE_TABLES))
        .delete(synchronize_session=False)
    )
    return deleted


def build_delivery_payload(row):
    return {
        "order_id": row["order_id"],
        "order_time": parse_iso_datetime(row["order_time"]),
        "main_dish": row["main_dish"],
        "order_price": round(parse_number(row["order_price"]), 2),
        "restaurant_lat": parse_number(row["restaurant_lat"]),
        "restaurant_lng": parse_number(row["restaurant_lng"]),
        "customer_lat": parse_number(row["customer_lat"]),
        "customer_lng": parse_number(row["customer_lng"]),
        "delivery_neighborhood": row["delivery_neighborhood"],
        "weather": row["weather"],
        "traffic_level": row["traffic_level"],
        "restaurant_busy_level": row["restaurant_busy_level"],
        "courier_name": row["courier_name"],
        "courier_vehicle": row["courier_vehicle"],
        "customer_first_name": row["customer_first_name"],
        "app_version": row["app_version"],
        "delivery_time_minutes": parse_number(row["delivery_time_minutes"], int),
        "quantity": 1,
        "status": "delivered",
    }


def import_delivery_train_records():
    rows = read_csv_rows(DELIVERIES_CSV)
    inserted = 0

    for row in rows:
        payload = build_delivery_payload(row)
        record = TrainRecord(
            source_table=DELIVERIES_SOURCE_TABLE,
            external_id=row["order_id"],
            payload_hash=TrainRecord.build_payload_hash(payload),
            payload=payload,
        )
        db.session.add(record)
        inserted += 1

    return rows, inserted


def build_demand_payload(row):
    return {
        "date": row["date"],
        "orders_total": parse_number(row["orders_total"], int),
        "revenue_total": round(parse_number(row["revenue_total"]), 2),
        "average_ticket": round(parse_number(row["average_ticket"]), 4),
        "weather": row["weather"],
        "traffic_level": row["traffic_level"],
        "day_of_week": parse_number(row["day_of_week"], int),
        "month": parse_number(row["month"], int),
        "orders_previous_day": parse_number(row["orders_previous_day"]),
        "orders_average_7_days": parse_number(row["orders_average_7_days"]),
    }


def import_daily_demand_records():
    rows = read_csv_rows(DEMAND_CSV)
    inserted = 0

    for row in rows:
        payload = build_demand_payload(row)
        record = TrainRecord(
            source_table=DEMAND_SOURCE_TABLE,
            external_id=row["date"],
            payload_hash=TrainRecord.build_payload_hash(payload),
            payload=payload,
        )
        db.session.add(record)
        inserted += 1

    return inserted


def seed_menu_items(owner, delivery_rows):
    grouped = defaultdict(lambda: {"count": 0, "revenue": 0.0})

    for row in delivery_rows:
        entry = grouped[row["main_dish"]]
        entry["count"] += 1
        entry["revenue"] += parse_number(row["order_price"])

    top_dishes = sorted(
        grouped.items(),
        key=lambda item: (-item[1]["count"], item[0]),
    )[:MENU_ITEM_LIMIT]

    MenuItem.query.filter_by(owner_id=owner.id).delete(synchronize_session=False)

    created = 0
    for name, stats in top_dishes:
        average_price = round(stats["revenue"] / stats["count"], 2)
        db.session.add(
            MenuItem(
                owner_id=owner.id,
                name=name,
                price=average_price,
            )
        )
        created += 1

    return created


def summarize_delivery_rows(rows):
    dish_counts = Counter(row["main_dish"] for row in rows)
    neighborhood_counts = Counter(row["delivery_neighborhood"] for row in rows)
    return {
        "unique_dishes": len(dish_counts),
        "top_dishes": dish_counts.most_common(5),
        "top_neighborhoods": neighborhood_counts.most_common(5),
    }


def populate_database():
    with app.app_context():
        db.create_all()

        owner = ensure_owner()
        deleted_seed_records = reset_seed_train_records()
        delivery_rows, inserted_delivery_records = import_delivery_train_records()
        inserted_demand_records = import_daily_demand_records()
        created_menu_items = seed_menu_items(owner, delivery_rows)

        db.session.commit()

        summary = summarize_delivery_rows(delivery_rows)
        owner_orders_count = TrainRecord.query.filter_by(
            source_table=OWNER_ORDERS_SOURCE_TABLE
        ).count()

        return {
            "owner_email": owner.email,
            "owner_password": DEFAULT_OWNER_PASSWORD,
            "deleted_seed_records": deleted_seed_records,
            "inserted_delivery_records": inserted_delivery_records,
            "inserted_demand_records": inserted_demand_records,
            "created_menu_items": created_menu_items,
            "preserved_owner_orders": owner_orders_count,
            "unique_dishes": summary["unique_dishes"],
            "top_dishes": summary["top_dishes"],
            "top_neighborhoods": summary["top_neighborhoods"],
        }


if __name__ == "__main__":
    result = populate_database()
    print("Database populated successfully.")
    print(f"Owner login: {result['owner_email']} / {result['owner_password']}")
    print(f"Removed old seeded train records: {result['deleted_seed_records']}")
    print(f"Inserted delivery train records: {result['inserted_delivery_records']}")
    print(f"Inserted demand daily records: {result['inserted_demand_records']}")
    print(f"Created menu items: {result['created_menu_items']}")
    print(f"Preserved owner orders: {result['preserved_owner_orders']}")
    print(f"Unique dishes in deliveries dataset: {result['unique_dishes']}")
    print(f"Top dishes: {result['top_dishes']}")
    print(f"Top neighborhoods: {result['top_neighborhoods']}")
