USE mytripdb;

ALTER TABLE region_list
    ADD COLUMN region_name_ko VARCHAR(100) NULL AFTER region_name;

UPDATE region_list
SET region_name_ko = CASE LOWER(TRIM(region_name))
    WHEN 'asia' THEN '아시아'
    WHEN 'europe' THEN '유럽'
    WHEN 'africa' THEN '아프리카'
    WHEN 'north america' THEN '북아메리카'
    WHEN 'south america' THEN '남아메리카'
    WHEN 'oceania' THEN '오세아니아'
    WHEN 'antarctica' THEN '남극'
    ELSE region_name
END;

ALTER TABLE region_list
    MODIFY COLUMN region_name_ko VARCHAR(100) NOT NULL;

CREATE OR REPLACE VIEW country_region_view AS
SELECT
    c.country_id,
    c.country_name,
    c.visit_status,
    c.visit_count,
    r.region_id,
    r.region_name,
    r.region_name_ko
FROM country_list c
LEFT JOIN region_list r
    ON c.region_id = r.region_id;
