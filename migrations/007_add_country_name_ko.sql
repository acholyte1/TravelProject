USE mytripdb;

ALTER TABLE country_list
    ADD COLUMN country_name_ko VARCHAR(100) NULL AFTER country_name;

CREATE OR REPLACE VIEW country_region_view AS
SELECT
    c.country_id,
    c.country_name,
    c.country_name_ko,
    c.visit_status,
    c.visit_count,
    r.region_id,
    r.region_name,
    r.region_name_ko
FROM country_list c
LEFT JOIN region_list r
    ON c.region_id = r.region_id;
