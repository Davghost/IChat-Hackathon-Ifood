import csv
import json
import secrets
import sqlite3
import string
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import scrypt, sha256
from pathlib import Path


DEFAULT_OWNER_EMAIL = "owner@hackathon.local"
DEFAULT_OWNER_USERNAME = "owner"
DEFAULT_OWNER_PASSWORD = "owner123"

DELIVERIES_SOURCE_TABLE = "train"
DEMAND_SOURCE_TABLE = "demand_daily"
OWNER_ORDERS_SOURCE_TABLE = "owner_orders"
SEED_SOURCE_TABLES = (DELIVERIES_SOURCE_TABLE, DEMAND_SOURCE_TABLE, "test")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
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


def build_payload_hash(payload):
    normalized_payload = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
    )
    return sha256(normalized_payload.encode("utf-8")).hexdigest()


def generate_password_hash(password: str) -> str:
    salt = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
    derived_key = scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=32768,
        r=8,
        p=1,
        dklen=64,
    )
    return f"scrypt:32768:8:1${salt}${derived_key.hex()}"


def ensure_schema(connection):
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY,
            username VARCHAR(64) NOT NULL,
            email VARCHAR(128) NOT NULL,
            password_hash VARCHAR(256),
            role VARCHAR(32) NOT NULL,
            created_at DATETIME
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY,
            owner_id INTEGER NOT NULL,
            name VARCHAR(120) NOT NULL,
            price FLOAT NOT NULL,
            created_at DATETIME NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS train_records (
            id INTEGER PRIMARY KEY,
            source_table VARCHAR(64) NOT NULL,
            external_id VARCHAR(128),
            payload_hash VARCHAR(64) NOT NULL,
            payload JSON NOT NULL,
            imported_at DATETIME NOT NULL
        )
        """
    )
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_user_email ON user (email)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_user_username ON user (username)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_train_records_payload_hash ON train_records (payload_hash)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_train_records_source_table ON train_records (source_table)")
    connection.commit()


def ensure_owner(connection):
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id FROM user WHERE email = ?",
        (DEFAULT_OWNER_EMAIL,),
    )
    row = cursor.fetchone()
    password_hash = generate_password_hash(DEFAULT_OWNER_PASSWORD)
    created_at = datetime.now(timezone.utc).isoformat()

    if row:
        owner_id = row[0]
        cursor.execute(
            """
            UPDATE user
            SET username = ?, role = ?, password_hash = ?
            WHERE id = ?
            """,
            (DEFAULT_OWNER_USERNAME, "owner", password_hash, owner_id),
        )
    else:
        cursor.execute(
            """
            INSERT INTO user (username, email, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                DEFAULT_OWNER_USERNAME,
                DEFAULT_OWNER_EMAIL,
                password_hash,
                "owner",
                created_at,
            ),
        )
        owner_id = cursor.lastrowid

    connection.commit()
    return owner_id


def clear_seed_data(connection, owner_id):
    cursor = connection.cursor()
    placeholders = ", ".join("?" for _ in SEED_SOURCE_TABLES)
    cursor.execute(
        f"DELETE FROM train_records WHERE source_table IN ({placeholders})",
        SEED_SOURCE_TABLES,
    )
    deleted_train_records = cursor.rowcount
    cursor.execute("DELETE FROM menu_items WHERE owner_id = ?", (owner_id,))
    deleted_menu_items = cursor.rowcount
    connection.commit()
    return deleted_train_records, deleted_menu_items


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


def import_delivery_train_records(connection):
    rows = read_csv_rows(DELIVERIES_CSV)
    cursor = connection.cursor()

    for row in rows:
        payload = build_delivery_payload(row)
        cursor.execute(
            """
            INSERT INTO train_records (source_table, external_id, payload_hash, payload, imported_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                DELIVERIES_SOURCE_TABLE,
                row["order_id"],
                build_payload_hash(payload),
                json.dumps(payload, ensure_ascii=False),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    connection.commit()
    return rows


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


def import_daily_demand_records(connection):
    rows = read_csv_rows(DEMAND_CSV)
    cursor = connection.cursor()

    for row in rows:
        payload = build_demand_payload(row)
        cursor.execute(
            """
            INSERT INTO train_records (source_table, external_id, payload_hash, payload, imported_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                DEMAND_SOURCE_TABLE,
                row["date"],
                build_payload_hash(payload),
                json.dumps(payload, ensure_ascii=False),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    connection.commit()
    return len(rows)


def seed_menu_items(connection, owner_id, delivery_rows):
    grouped = defaultdict(lambda: {"count": 0, "revenue": 0.0})
    for row in delivery_rows:
        entry = grouped[row["main_dish"]]
        entry["count"] += 1
        entry["revenue"] += parse_number(row["order_price"])

    top_dishes = sorted(
        grouped.items(),
        key=lambda item: (-item[1]["count"], item[0]),
    )[:MENU_ITEM_LIMIT]

    cursor = connection.cursor()
    created_at = datetime.now(timezone.utc).isoformat()
    for name, stats in top_dishes:
        average_price = round(stats["revenue"] / stats["count"], 2)
        cursor.execute(
            """
            INSERT INTO menu_items (owner_id, name, price, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (owner_id, name, average_price, created_at),
        )

    connection.commit()
    return len(top_dishes)


def summarize_delivery_rows(rows):
    dish_counts = Counter(row["main_dish"] for row in rows)
    neighborhood_counts = Counter(row["delivery_neighborhood"] for row in rows)
    return {
        "unique_dishes": len(dish_counts),
        "top_dishes": dish_counts.most_common(5),
        "top_neighborhoods": neighborhood_counts.most_common(5),
    }


def count_owner_orders(connection):
    cursor = connection.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM train_records WHERE source_table = ?",
        (OWNER_ORDERS_SOURCE_TABLE,),
    )
    return cursor.fetchone()[0]


def populate_database():
    connection = sqlite3.connect(DB_PATH)

    try:
        ensure_schema(connection)
        owner_id = ensure_owner(connection)
        deleted_train_records, deleted_menu_items = clear_seed_data(connection, owner_id)
        delivery_rows = import_delivery_train_records(connection)
        inserted_demand_records = import_daily_demand_records(connection)
        created_menu_items = seed_menu_items(connection, owner_id, delivery_rows)
        summary = summarize_delivery_rows(delivery_rows)

        return {
            "owner_email": DEFAULT_OWNER_EMAIL,
            "owner_password": DEFAULT_OWNER_PASSWORD,
            "owner_id": owner_id,
            "deleted_train_records": deleted_train_records,
            "deleted_menu_items": deleted_menu_items,
            "inserted_delivery_records": len(delivery_rows),
            "inserted_demand_records": inserted_demand_records,
            "created_menu_items": created_menu_items,
            "preserved_owner_orders": count_owner_orders(connection),
            "unique_dishes": summary["unique_dishes"],
            "top_dishes": summary["top_dishes"],
            "top_neighborhoods": summary["top_neighborhoods"],
        }
    finally:
        connection.close()


if __name__ == "__main__":
    result = populate_database()
    print("Database populated successfully.")
    print(f"Owner login: {result['owner_email']} / {result['owner_password']}")
    print(f"Owner id: {result['owner_id']}")
    print(f"Removed old seeded train records: {result['deleted_train_records']}")
    print(f"Removed old menu items: {result['deleted_menu_items']}")
    print(f"Inserted delivery train records: {result['inserted_delivery_records']}")
    print(f"Inserted demand daily records: {result['inserted_demand_records']}")
    print(f"Created menu items: {result['created_menu_items']}")
    print(f"Preserved owner orders: {result['preserved_owner_orders']}")
    print(f"Unique dishes in deliveries dataset: {result['unique_dishes']}")
    print(f"Top dishes: {result['top_dishes']}")
    print(f"Top neighborhoods: {result['top_neighborhoods']}")
