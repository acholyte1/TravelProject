USE mytripdb;

ALTER TABLE location_list
    ADD COLUMN location_name_ko VARCHAR(100) NULL AFTER location_name;
