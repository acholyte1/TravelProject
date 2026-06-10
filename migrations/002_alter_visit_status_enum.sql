-- Pending migration.
-- Restrict visit_status to known states.
-- Check existing values before running if these tables already contain data.

SELECT visit_status, COUNT(*)
FROM country_list
WHERE visit_status IS NOT NULL
  AND visit_status NOT IN ('TRIP', 'STAY', 'WANT')
GROUP BY visit_status;

SELECT visit_status, COUNT(*)
FROM location_list
WHERE visit_status IS NOT NULL
  AND visit_status NOT IN ('TRIP', 'STAY', 'WANT')
GROUP BY visit_status;

ALTER TABLE country_list
MODIFY visit_status ENUM('TRIP', 'STAY', 'WANT') NULL;

ALTER TABLE location_list
MODIFY visit_status ENUM('TRIP', 'STAY', 'WANT') NULL;
