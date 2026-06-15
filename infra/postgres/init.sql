-- Gold layer schema + read-only role for Text-to-SQL agent
CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.customers (
    customer_id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150),
    phone VARCHAR(20),
    pan VARCHAR(10),
    account_number VARCHAR(18) NOT NULL UNIQUE,
    kyc_status VARCHAR(20) DEFAULT 'verified',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gold.transactions (
    transaction_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES gold.customers(customer_id),
    account_number VARCHAR(18) NOT NULL,
    transaction_date DATE NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    category VARCHAR(50),
    merchant VARCHAR(100),
    amount DECIMAL(12, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    status VARCHAR(20) DEFAULT 'completed',
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_txn_date ON gold.transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_txn_account ON gold.transactions(account_number);
CREATE INDEX IF NOT EXISTS idx_txn_type ON gold.transactions(transaction_type);

-- Row-level security example (optional learning exercise)
ALTER TABLE gold.transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY txn_read_policy ON gold.transactions
    FOR SELECT
    USING (true);

-- Read-only role — agent can only SELECT
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'agent_readonly') THEN
        CREATE ROLE agent_readonly LOGIN PASSWORD 'readonly_agent_password';
    END IF;
END
$$;

GRANT USAGE ON SCHEMA gold TO agent_readonly;
GRANT SELECT ON gold.customers, gold.transactions TO agent_readonly;
