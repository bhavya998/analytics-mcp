"""SQLite database with realistic enterprise sales schema and seed data.

Tables: customers, products, orders, order_items, employees
Seed: 200+ customers, 50 products, 2000+ orders across 12 months.
"""

from __future__ import annotations

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent.parent.parent / "data" / "enterprise.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    company TEXT,
    region TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'standard',
    signup_date TEXT NOT NULL,
    lifetime_value REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL,
    cost REAL NOT NULL,
    stock INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    region TEXT NOT NULL,
    hire_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    employee_id INTEGER,
    order_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed',
    total REAL NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);
"""

REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East"]
TIERS = ["standard", "premium", "enterprise"]
CATEGORIES = ["Electronics", "Software", "Services", "Hardware", "Consulting"]
STATUSES = ["completed", "pending", "cancelled", "refunded"]

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Aisha", "Wei", "Hiroshi", "Priya",
    "Omar", "Yuki", "Diego", "Fatima", "Chen", "Anya",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    "Kumar", "Tanaka", "Kim", "Singh", "Patel", "Nguyen", "Chang", "Okafor",
]
COMPANY_PREFIXES = ["Tech", "Data", "Cloud", "Cyber", "Quantum", "Nexus", "Vertex", "Apex", "Prime", "Meta"]
COMPANY_SUFFIXES = ["Corp", "Solutions", "Systems", "Labs", "Group", "Industries", "Partners", "Holdings"]
PRODUCT_NAMES = {
    "Electronics": ["Pro Laptop 15", "Ultra Tablet", "4K Monitor", "Wireless Headset", "Smart Hub"],
    "Software": ["Enterprise Suite", "Security Platform", "Analytics Dashboard", "CRM Pro", "DevOps Toolkit"],
    "Services": ["Premium Support", "Implementation Package", "Training Program", "Health Check", "Migration Service"],
    "Hardware": ["Rack Server X1", "Network Switch 48G", "Storage Array 100TB", "Backup Appliance", "Edge Gateway"],
    "Consulting": ["Strategy Session", "Architecture Review", "Security Audit", "Performance Tuning", "Compliance Check"],
}


def init_database(db_path: Path | str | None = None, force_reseed: bool = False) -> str:
    """Initialize the SQLite database with schema and seed data.

    Args:
        db_path: Path to the database file. Defaults to data/enterprise.db.
        force_reseed: If True, drop and recreate all data.

    Returns:
        Path to the created database file.
    """
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    if force_reseed and path.exists():
        path.unlink()

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.executescript(SCHEMA_SQL)

    # Check if data already exists
    count = cursor.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    if count == 0 or force_reseed:
        _seed_data(cursor)
        conn.commit()

    conn.close()
    return str(path)


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Get a SQLite connection with row factory enabled.

    Args:
        db_path: Path to the database file. Defaults to data/enterprise.db.

    Returns:
        SQLite connection with Row factory.
    """
    path = Path(db_path) if db_path else DB_PATH
    if not path.exists():
        init_database(path)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def query_db(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """Execute a SELECT query and return results as dicts.

    Args:
        sql: SQL query string (must be SELECT).
        params: Parameterized query values.

    Returns:
        List of row dicts.

    Raises:
        ValueError: If the query is not a SELECT statement.
    """
    if not sql.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_schema_info() -> dict[str, Any]:
    """Get the full database schema information.

    Returns:
        Dict mapping table names to their column info.
    """
    conn = get_connection()
    try:
        tables = query_db(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        schema: dict[str, Any] = {}
        for table_row in tables:
            table_name = table_row["name"]
            columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            schema[table_name] = {
                "columns": [
                    {
                        "name": col[1],
                        "type": col[2],
                        "nullable": not col[3],
                        "primary_key": bool(col[5]),
                    }
                    for col in columns
                ],
                "row_count": conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0],
            }
        return schema
    finally:
        conn.close()


def _seed_data(cursor: sqlite3.Cursor) -> None:
    """Seed the database with realistic enterprise data."""
    random.seed(42)

    cursor.executescript("DELETE FROM order_items; DELETE FROM orders; DELETE FROM products; DELETE FROM customers; DELETE FROM employees;")

    # Employees
    employees = []
    for i, region in enumerate(REGIONS):
        for j in range(3):
            name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            role = random.choice(["Sales Rep", "Sales Manager", "Account Executive"])
            hire_date = (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 730))).strftime("%Y-%m-%d")
            emp_id = i * 3 + j + 1
            employees.append((emp_id, name, role, region, hire_date))
    cursor.executemany("INSERT INTO employees VALUES (?,?,?,?,?)", employees)

    # Customers
    customers = []
    for i in range(200):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        email = f"{name.lower().replace(' ', '.')}@{random.choice(COMPANY_PREFIXES).lower()}{random.choice(COMPANY_SUFFIXES).lower()}.com"
        company = f"{random.choice(COMPANY_PREFIXES)} {random.choice(COMPANY_SUFFIXES)}"
        region = random.choice(REGIONS)
        tier = random.choices(TIERS, weights=[60, 30, 10])[0]
        signup_date = (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 730))).strftime("%Y-%m-%d")
        customers.append((i + 1, name, email, company, region, tier, signup_date, 0.0))
    cursor.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?)", customers)

    # Products
    products = []
    pid = 1
    for category, names in PRODUCT_NAMES.items():
        for pname in names:
            price = round(random.uniform(99, 9999), 2)
            cost = round(price * random.uniform(0.3, 0.6), 2)
            stock = random.randint(10, 500)
            products.append((pid, pname, category, price, cost, stock))
            pid += 1
    cursor.executemany("INSERT INTO products VALUES (?,?,?,?,?,?)", products)

    # Orders + order_items
    orders = []
    order_items = []
    oi_id = 1
    for order_id in range(1, 2001):
        customer_id = random.randint(1, 200)
        employee_id = random.randint(1, len(employees))
        order_date = (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 546))).strftime("%Y-%m-%d")
        status = random.choices(STATUSES, weights=[80, 10, 5, 5])[0]

        num_items = random.randint(1, 5)
        selected_products = random.sample(products, num_items)
        total = 0.0
        for prod in selected_products:
            qty = random.randint(1, 20)
            unit_price = prod[3]
            total += qty * unit_price
            order_items.append((oi_id, order_id, prod[0], qty, unit_price))
            oi_id += 1

        total = round(total, 2)
        orders.append((order_id, customer_id, employee_id, order_date, status, total))

    cursor.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?)", orders)
    cursor.executemany("INSERT INTO order_items VALUES (?,?,?,?,?)", order_items)

    # Update lifetime_value
    cursor.execute("""
        UPDATE customers SET lifetime_value = (
            SELECT COALESCE(SUM(o.total), 0)
            FROM orders o
            WHERE o.customer_id = customers.id AND o.status = 'completed'
        )
    """)
