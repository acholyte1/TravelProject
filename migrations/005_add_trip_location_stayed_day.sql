ALTER TABLE trip_location_list
ADD COLUMN stayed_day INT AFTER location_out;

UPDATE trip_location_list
SET stayed_day = DATEDIFF(location_out, location_in)
WHERE location_in IS NOT NULL
  AND location_out IS NOT NULL;
