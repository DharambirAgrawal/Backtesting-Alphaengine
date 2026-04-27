-- Add idempotency key to deduplicate repeated trade inserts from concurrent runs.
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(255);

-- Enforce uniqueness only for populated keys.
CREATE UNIQUE INDEX IF NOT EXISTS uq_transactions_idempotency_key
ON transactions (idempotency_key)
WHERE idempotency_key IS NOT NULL;
