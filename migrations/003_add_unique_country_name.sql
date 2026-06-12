-- Pending migration.
-- Review the first query before applying the data cleanup and constraint.

SELECT TRIM(country_name) AS normalized_country_name, COUNT(*) AS duplicate_count
FROM country_list
GROUP BY TRIM(country_name)
HAVING COUNT(*) > 1;

-- If the query above returns rows, merge or delete those duplicates first.
UPDATE country_list
SET country_name = TRIM(country_name);

ALTER TABLE country_list
ADD CONSTRAINT uq_country_list_country_name UNIQUE (country_name);
