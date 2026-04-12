-- ============================================================
-- DAItaView Test Database – Mock Data
-- ============================================================

-- ── Salespeople ──────────────────────────────────────────────
INSERT INTO salespeople (name, region, hire_date) VALUES
  ('Alice Chen',    'West',      '2019-03-12'),
  ('Bob Martinez',  'East',      '2020-07-01'),
  ('Carol Kim',     'North',     '2018-11-20'),
  ('David Okafor',  'South',     '2021-02-14'),
  ('Eva Rossi',     'West',      '2022-06-05'),
  ('Frank Nguyen',  'East',      '2017-09-30'),
  ('Grace Patel',   'North',     '2023-01-10'),
  ('Henry Walsh',   'South',     '2020-04-22');

-- ── Products ─────────────────────────────────────────────────
INSERT INTO products (name, category, unit_price, stock_quantity) VALUES
  ('Analytics Pro',        'Software',   299.00,  999),
  ('Dashboard Starter',    'Software',    49.00,  999),
  ('Enterprise Suite',     'Software',  1200.00,  999),
  ('Data Connector Pack',  'Add-on',     149.00,  999),
  ('Training Workshop',    'Service',    399.00,  200),
  ('Premium Support Plan', 'Service',    599.00,  500),
  ('Cloud Storage 1TB',    'Cloud',       19.00, 9999),
  ('Cloud Storage 10TB',   'Cloud',      149.00, 9999),
  ('API Access Token',     'Add-on',      29.00,  999),
  ('Custom Integration',   'Service',   2500.00,   50);

-- ── Customers ────────────────────────────────────────────────
INSERT INTO customers (name, email, region, tier, signup_date, is_active) VALUES
  ('Acme Corp',           'billing@acme.com',         'West',  'platinum', '2020-01-15', TRUE),
  ('Bright Analytics',    'admin@brightanalytics.io', 'East',  'gold',     '2021-03-22', TRUE),
  ('Cedar Technologies',  'ops@cedartec.com',         'North', 'silver',   '2022-06-10', TRUE),
  ('Delta Insights',      'contact@deltainsights.ai', 'South', 'gold',     '2020-09-05', TRUE),
  ('Echo Ventures',       'team@echoventures.co',     'West',  'bronze',   '2023-02-18', TRUE),
  ('Frontier Data',       'info@frontierdata.net',    'East',  'platinum', '2019-11-01', TRUE),
  ('Global Metrics',      'hello@globalmetrics.com',  'North', 'silver',   '2021-07-30', TRUE),
  ('Horizon Systems',     'buy@horizonsys.io',        'South', 'bronze',   '2022-12-03', TRUE),
  ('Iris Research',       'research@iris.org',        'West',  'gold',     '2020-04-14', TRUE),
  ('Jade Consulting',     'hello@jadeconsult.biz',    'East',  'silver',   '2023-05-09', TRUE),
  ('Kestrel Finance',     'ops@kestrelfinance.com',   'North', 'platinum', '2018-08-20', TRUE),
  ('Luminary Labs',       'dev@luminarylabs.dev',     'South', 'bronze',   '2023-09-01', FALSE),
  ('Metro Analytics',     'info@metroanalytics.com',  'West',  'gold',     '2021-01-11', TRUE),
  ('Nexus Dynamics',      'nexus@nexusdyn.io',        'East',  'silver',   '2022-04-17', TRUE),
  ('Orbit Solutions',     'sales@orbitsol.com',       'North', 'platinum', '2019-06-25', TRUE);

-- ── Sales (2023-01-01 through 2024-03-31) ────────────────────
INSERT INTO sales (sale_date, customer_id, product_id, salesperson_id, quantity, unit_price, discount_pct) VALUES
-- 2023 Q1
  ('2023-01-05',  1,  3, 1,  2, 1200.00, 10),
  ('2023-01-12',  2,  1, 2,  3,  299.00,  5),
  ('2023-01-19',  3,  2, 3,  5,   49.00,  0),
  ('2023-01-25',  4,  5, 4,  1,  399.00,  0),
  ('2023-02-03',  5,  7, 5, 10,   19.00,  0),
  ('2023-02-10',  6,  4, 6,  2,  149.00,  5),
  ('2023-02-17',  7,  6, 7,  1,  599.00,  0),
  ('2023-02-24',  8,  1, 8,  2,  299.00,  0),
  ('2023-03-03',  9,  3, 1,  1, 1200.00, 15),
  ('2023-03-11', 10,  2, 2,  3,   49.00,  0),
  ('2023-03-18', 11, 10, 3,  1, 2500.00,  5),
  ('2023-03-25', 12,  5, 4,  2,  399.00,  0),
-- 2023 Q2
  ('2023-04-06',  1,  6, 1,  2,  599.00,  5),
  ('2023-04-14',  2,  9, 2,  5,   29.00,  0),
  ('2023-04-21',  3,  1, 3,  4,  299.00,  0),
  ('2023-04-28',  4,  8, 4,  2,  149.00,  0),
  ('2023-05-05',  5,  3, 5,  1, 1200.00, 20),
  ('2023-05-13',  6,  7, 6, 20,   19.00,  0),
  ('2023-05-20',  7,  4, 7,  3,  149.00,  5),
  ('2023-05-27',  8,  2, 8,  6,   49.00,  0),
  ('2023-06-04',  9,  5, 1,  1,  399.00,  0),
  ('2023-06-12', 10,  1, 2,  2,  299.00,  0),
  ('2023-06-19', 11,  6, 3,  3,  599.00, 10),
  ('2023-06-26', 12,  3, 4,  1, 1200.00,  0),
-- 2023 Q3
  ('2023-07-07', 13,  1, 5,  5,  299.00,  5),
  ('2023-07-15', 14,  4, 6,  2,  149.00,  0),
  ('2023-07-22', 15,  3, 7,  2, 1200.00, 10),
  ('2023-07-29',  1,  9, 8, 10,   29.00,  0),
  ('2023-08-05',  2,  5, 1,  2,  399.00,  0),
  ('2023-08-12',  3,  6, 2,  1,  599.00,  5),
  ('2023-08-19',  4,  7, 3, 30,   19.00,  0),
  ('2023-08-26',  5,  1, 4,  3,  299.00,  0),
  ('2023-09-02',  6, 10, 5,  1, 2500.00,  0),
  ('2023-09-10',  7,  2, 6,  4,   49.00,  0),
  ('2023-09-17',  8,  3, 7,  1, 1200.00, 15),
  ('2023-09-24',  9,  4, 8,  2,  149.00,  0),
-- 2023 Q4
  ('2023-10-01', 10,  1, 1,  6,  299.00,  0),
  ('2023-10-09', 11,  5, 2,  2,  399.00,  5),
  ('2023-10-16', 12,  6, 3,  1,  599.00,  0),
  ('2023-10-23', 13,  3, 4,  3, 1200.00, 10),
  ('2023-11-04', 14,  7, 5, 15,   19.00,  0),
  ('2023-11-11', 15,  4, 6,  3,  149.00,  0),
  ('2023-11-18',  1,  1, 7,  5,  299.00,  0),
  ('2023-11-25',  2,  8, 8, 10,  149.00,  5),
  ('2023-12-02',  3,  3, 1,  2, 1200.00, 20),
  ('2023-12-10',  4,  6, 2,  2,  599.00,  0),
  ('2023-12-17',  5,  5, 3,  3,  399.00,  0),
  ('2023-12-26',  6, 10, 4,  1, 2500.00, 10),
-- 2024 Q1
  ('2024-01-08',  7,  1, 5,  4,  299.00,  0),
  ('2024-01-15',  8,  3, 6,  1, 1200.00,  5),
  ('2024-01-22',  9,  2, 7,  5,   49.00,  0),
  ('2024-01-29', 10,  6, 8,  2,  599.00,  0),
  ('2024-02-05', 11,  4, 1,  3,  149.00,  0),
  ('2024-02-12', 12,  7, 2, 25,   19.00,  0),
  ('2024-02-19', 13,  5, 3,  2,  399.00,  5),
  ('2024-02-26', 14,  1, 4,  3,  299.00,  0),
  ('2024-03-04', 15,  3, 5,  2, 1200.00, 10),
  ('2024-03-11',  1,  9, 6, 20,   29.00,  0),
  ('2024-03-18',  2,  6, 7,  1,  599.00,  0),
  ('2024-03-25',  3, 10, 8,  1, 2500.00,  5);

-- ── Support Tickets ───────────────────────────────────────────
INSERT INTO support_tickets (customer_id, opened_at, closed_at, priority, category, resolved) VALUES
  ( 1, '2023-02-10 09:15:00', '2023-02-11 14:30:00', 'high',     'billing',       TRUE),
  ( 2, '2023-03-05 11:00:00', '2023-03-06 10:45:00', 'medium',   'integration',   TRUE),
  ( 3, '2023-04-20 14:22:00', '2023-04-21 09:00:00', 'low',      'general',       TRUE),
  ( 4, '2023-05-15 08:30:00', '2023-05-16 17:00:00', 'critical', 'data loss',     TRUE),
  ( 5, '2023-06-01 13:00:00', NULL,                  'medium',   'performance',   FALSE),
  ( 6, '2023-06-18 10:45:00', '2023-06-19 11:30:00', 'high',     'access',        TRUE),
  ( 7, '2023-07-03 09:00:00', '2023-07-04 16:00:00', 'low',      'general',       TRUE),
  ( 8, '2023-08-22 15:30:00', NULL,                  'medium',   'billing',       FALSE),
  ( 9, '2023-09-10 10:00:00', '2023-09-10 15:00:00', 'critical', 'data loss',     TRUE),
  (10, '2023-10-05 11:15:00', '2023-10-06 09:30:00', 'high',     'integration',   TRUE),
  (11, '2023-11-12 14:00:00', '2023-11-14 10:00:00', 'medium',   'performance',   TRUE),
  (12, '2023-12-01 08:45:00', NULL,                  'low',      'general',       FALSE),
  (13, '2024-01-15 13:30:00', '2024-01-15 17:00:00', 'high',     'access',        TRUE),
  (14, '2024-02-08 09:00:00', '2024-02-09 12:00:00', 'medium',   'billing',       TRUE),
  (15, '2024-03-01 10:00:00', NULL,                  'critical', 'data loss',     FALSE),
  ( 1, '2024-03-10 14:00:00', '2024-03-11 09:00:00', 'high',     'integration',   TRUE),
  ( 2, '2024-03-20 11:30:00', NULL,                  'medium',   'performance',   FALSE);
