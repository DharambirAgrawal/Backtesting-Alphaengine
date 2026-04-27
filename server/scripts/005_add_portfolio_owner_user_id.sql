-- Add portfolio ownership without losing existing rows.
ALTER TABLE portfolios
ADD COLUMN IF NOT EXISTS owner_user_id UUID;

-- Assign all existing portfolios to the admin user so nothing is lost or broken.
UPDATE portfolios SET owner_user_id = (
    SELECT id FROM users WHERE role = 'admin' LIMIT 1
);

-- Make the ownership column required for all future portfolios.
ALTER TABLE portfolios
ALTER COLUMN owner_user_id SET NOT NULL;

ALTER TABLE portfolios
ADD CONSTRAINT fk_portfolios_owner_user_id
FOREIGN KEY (owner_user_id)
REFERENCES users(id)
ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_portfolios_owner_user_id
ON portfolios (owner_user_id);
