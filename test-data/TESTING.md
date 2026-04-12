# DAItaView — Test Data & Testing Guide

This folder contains everything needed to spin up a self-contained PostgreSQL test database
and flat-file samples for exercising every data-source type supported by DAItaView.

---

## Folder structure

```
test-data/
├── docker-compose.yml      # Postgres test container (port 5433)
├── init/
│   ├── 01_schema.sql       # Table definitions
│   └── 02_mock_data.sql    # ~100 rows across 5 tables
├── mock_sales.csv          # 60-row CSV: flat sales fact table
├── mock_customers.json     # 15-record JSON: customers with nested KPIs
└── TESTING.md              # This file
```

---

## 1. Start the test database

```bash
cd test-data
docker compose up -d
```

Wait until the container is healthy (≈5 s):

```bash
docker compose ps
# testdb   running (healthy)
```

The database is reachable at:

| Setting  | Value     |
|----------|-----------|
| Host     | localhost |
| Port     | **5433**  |
| Database | testdb    |
| User     | testuser  |
| Password | testpass  |

Connection string:

```
postgresql://testuser:testpass@localhost:5433/testdb
```

### Verify the data

```bash
docker exec -it daitaview-testdb psql -U testuser -d testdb -c "\dt"
# Should list: customers, products, salespeople, sales, support_tickets

docker exec -it daitaview-testdb psql -U testuser -d testdb \
  -c "SELECT COUNT(*) FROM sales;"
# → 60
```

---

## 2. Connect to DAItaView

1. Open the app at **http://localhost:3000** and log in.
2. Go to **Admin → Data Sources**.
3. Click **Add Data Source** and fill in:
   - **Type**: PostgreSQL
   - **Name**: `Test DB`
   - **Connection string**: `postgresql://testuser:testpass@host.docker.internal:5433/testdb`
     *(use `host.docker.internal` so the backend container can reach your host's port 5433)*
4. Click **Save & Introspect** — the schema (tables + columns) will be detected automatically.

For flat-file sources, use the **Upload** button on the Data Sources page:
- Upload `mock_sales.csv` as a CSV source named `Sales CSV`
- Upload `mock_customers.json` as a JSON source named `Customer JSON`

---

## 3. Database schema overview

### `customers` (15 rows)
| Column      | Type    | Notes                              |
|-------------|---------|------------------------------------|
| id          | int PK  |                                    |
| name        | varchar |                                    |
| email       | varchar | unique                             |
| region      | varchar | West / East / North / South        |
| tier        | varchar | bronze / silver / gold / platinum  |
| signup_date | date    |                                    |
| is_active   | bool    | 1 inactive customer (Luminary Labs)|

### `products` (10 rows)
| Column         | Type    | Notes                              |
|----------------|---------|------------------------------------|
| id             | int PK  |                                    |
| name           | varchar |                                    |
| category       | varchar | Software / Service / Cloud / Add-on|
| unit_price     | numeric |                                    |
| stock_quantity | int     |                                    |

### `salespeople` (8 rows)
| Column    | Type    | Notes               |
|-----------|---------|---------------------|
| id        | int PK  |                     |
| name      | varchar |                     |
| region    | varchar |                     |
| hire_date | date    |                     |

### `sales` (60 rows — Jan 2023 through Mar 2024)
| Column          | Type    | Notes                          |
|-----------------|---------|--------------------------------|
| id              | int PK  |                                |
| sale_date       | date    |                                |
| customer_id     | int FK  | → customers                    |
| product_id      | int FK  | → products                     |
| salesperson_id  | int FK  | → salespeople                  |
| quantity        | int     |                                |
| unit_price      | numeric |                                |
| discount_pct    | numeric | 0–20                           |
| total_amount    | numeric | computed: qty × price × (1-disc)|

### `support_tickets` (17 rows)
| Column      | Type      | Notes                               |
|-------------|-----------|-------------------------------------|
| id          | int PK    |                                     |
| customer_id | int FK    | → customers                         |
| opened_at   | timestamp |                                     |
| closed_at   | timestamp | NULL = still open                   |
| priority    | varchar   | low / medium / high / critical      |
| category    | varchar   | billing / integration / general / …|
| resolved    | bool      | 4 unresolved tickets                |

---

## 4. Sample natural-language queries to test

Use these in the DAItaView chat after connecting the `Test DB` source.

### Basic aggregations
- "What is the total revenue for each product category in 2023?"
- "How many sales were made per region last year?"
- "Show me the top 5 customers by total spend."

### Time-series
- "Plot monthly revenue for 2023 as a line chart."
- "Compare Q1 2023 vs Q1 2024 total revenue."
- "What was the average order value each quarter in 2023?"

### Joins & filtering
- "Which platinum-tier customers made more than 3 purchases?"
- "List all sales where the discount was above 10%."
- "Show me the salespeople who closed the most deals in the West region."

### Multi-table / complex
- "For each customer, show their total revenue and number of open support tickets."
- "Which products have the highest revenue but also the most critical support tickets?"
- "Rank salespeople by total revenue generated in 2023."

### Flat-file (CSV / JSON source)
- "What is the average total_amount per customer_tier from the sales CSV?"
- "Show a bar chart of revenue by product_category from the CSV."
- "From the customer JSON, which region has the most platinum customers?"
- "List all customers in the JSON whose open_tickets count is greater than 0."

---

## 5. Expected chart & table output

| Query type                    | Expected result type |
|-------------------------------|----------------------|
| Monthly/quarterly time-series | Line chart           |
| Revenue by category/region    | Bar chart            |
| Distribution (tiers, priority)| Pie / bar chart      |
| Ranked lists / top-N          | Sortable table       |
| Single scalar (total, count)  | Table (1 row)        |

---

## 6. Tear down

```bash
cd test-data
docker compose down          # stop container, keep volume
docker compose down -v       # stop container AND delete volume (fresh start)
```

---

## 7. Resetting the data

To wipe and reload all mock data without rebuilding the image:

```bash
docker compose down -v
docker compose up -d
```

The `init/` scripts run automatically on first start (when the volume is empty).
