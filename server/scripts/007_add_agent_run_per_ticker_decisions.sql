ALTER TABLE agent_runs
ADD COLUMN IF NOT EXISTS per_ticker_decisions JSONB;
