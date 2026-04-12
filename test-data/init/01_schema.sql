-- ============================================================
-- DAItaView Test Database Schema
-- ============================================================

CREATE TABLE IF NOT EXISTS customers (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(150) UNIQUE NOT NULL,
    region      VARCHAR(50)  NOT NULL,
    tier        VARCHAR(20)  NOT NULL CHECK (tier IN ('bronze', 'silver', 'gold', 'platinum')),
    signup_date DATE         NOT NULL,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS products (
    id             SERIAL PRIMARY KEY,
    name           VARCHAR(120) NOT NULL,
    category       VARCHAR(60)  NOT NULL,
    unit_price     NUMERIC(10,2) NOT NULL,
    stock_quantity INT          NOT NULL DEFAULT 0,
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS salespeople (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    region     VARCHAR(50)  NOT NULL,
    hire_date  DATE         NOT NULL
);

CREATE TABLE IF NOT EXISTS sales (
    id            SERIAL PRIMARY KEY,
    sale_date     DATE         NOT NULL,
    customer_id   INT          NOT NULL REFERENCES customers(id),
    product_id    INT          NOT NULL REFERENCES products(id),
    salesperson_id INT         NOT NULL REFERENCES salespeople(id),
    quantity      INT          NOT NULL,
    unit_price    NUMERIC(10,2) NOT NULL,
    discount_pct  NUMERIC(5,2) NOT NULL DEFAULT 0,
    total_amount  NUMERIC(12,2) GENERATED ALWAYS AS (
                    quantity * unit_price * (1 - discount_pct / 100)
                  ) STORED
);

CREATE TABLE IF NOT EXISTS support_tickets (
    id           SERIAL PRIMARY KEY,
    customer_id  INT         NOT NULL REFERENCES customers(id),
    opened_at    TIMESTAMP   NOT NULL,
    closed_at    TIMESTAMP,
    priority     VARCHAR(20) NOT NULL CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    category     VARCHAR(60) NOT NULL,
    resolved     BOOLEAN     NOT NULL DEFAULT FALSE
);

-- Indexes for typical analytical queries
CREATE INDEX idx_sales_date         ON sales(sale_date);
CREATE INDEX idx_sales_customer     ON sales(customer_id);
CREATE INDEX idx_sales_product      ON sales(product_id);
CREATE INDEX idx_sales_salesperson  ON sales(salesperson_id);
CREATE INDEX idx_tickets_customer   ON support_tickets(customer_id);
CREATE INDEX idx_tickets_opened     ON support_tickets(opened_at);
