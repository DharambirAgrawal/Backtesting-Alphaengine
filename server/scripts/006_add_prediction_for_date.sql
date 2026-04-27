ALTER TABLE prediction_history
ADD COLUMN IF NOT EXISTS prediction_for_date DATE;

UPDATE prediction_history
SET prediction_for_date = prediction_date
WHERE prediction_for_date IS NULL;

CREATE INDEX IF NOT EXISTS idx_prediction_history_prediction_for_date
ON prediction_history (prediction_for_date);

CREATE INDEX IF NOT EXISTS idx_prediction_history_unresolved_due
ON prediction_history (prediction_for_date)
WHERE actual_price IS NULL;
