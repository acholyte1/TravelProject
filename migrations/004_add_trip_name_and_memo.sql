ALTER TABLE trip_list
ADD COLUMN trip_name VARCHAR(100) NOT NULL AFTER trip_id,
ADD COLUMN trip_memo TEXT AFTER trip_name;

UPDATE trip_list
SET trip_name = CONCAT('Trip ', trip_id)
WHERE trip_name = '';
