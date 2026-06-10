-- Applied manually on 2026-06-10.
-- Make trip_list.trip_id auto-generated while preserving dependent foreign keys.
-- Note: migrations/000_init_schema.sql already includes AUTO_INCREMENT for fresh installs.
-- Keep this file as a record/fix for databases that were created without it.

ALTER TABLE trip_country_list
DROP FOREIGN KEY fk_trip_country_trip;

ALTER TABLE trip_location_list
DROP FOREIGN KEY fk_trip_location_trip;

ALTER TABLE trip_list
MODIFY trip_id INT NOT NULL AUTO_INCREMENT;

ALTER TABLE trip_country_list
ADD CONSTRAINT fk_trip_country_trip
FOREIGN KEY (trip_id) REFERENCES trip_list (trip_id);

ALTER TABLE trip_location_list
ADD CONSTRAINT fk_trip_location_trip
FOREIGN KEY (trip_id) REFERENCES trip_list (trip_id);
