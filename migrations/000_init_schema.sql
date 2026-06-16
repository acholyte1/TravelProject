CREATE DATABASE IF NOT EXISTS mytripdb;
USE mytripdb;

CREATE TABLE region_list (
    region_id INT AUTO_INCREMENT PRIMARY KEY,
    region_name VARCHAR(100) NOT NULL
);

CREATE TABLE country_list (
    country_id INT AUTO_INCREMENT PRIMARY KEY,
    country_name VARCHAR(100) NOT NULL UNIQUE,
    visit_status VARCHAR(20),
    visit_count INT DEFAULT 0,
    region_id INT,
    CONSTRAINT fk_country_region
        FOREIGN KEY (region_id)
        REFERENCES region_list(region_id)
);

CREATE TABLE location_list (
    location_id INT AUTO_INCREMENT PRIMARY KEY,
    country_id INT NOT NULL,
    location_name VARCHAR(100) NOT NULL,
    visit_status VARCHAR(20),
    visit_count INT DEFAULT 0,
    region_id INT,
    CONSTRAINT fk_location_country
        FOREIGN KEY (country_id)
        REFERENCES country_list(country_id),
    CONSTRAINT fk_location_region
        FOREIGN KEY (region_id)
        REFERENCES region_list(region_id)
);

CREATE TABLE trip_list (
    trip_id INT AUTO_INCREMENT PRIMARY KEY,
    trip_name VARCHAR(100) NOT NULL,
    trip_memo TEXT,
    in_date DATE,
    out_date DATE,
    stayed_day INT,
    is_deleted TINYINT DEFAULT 0
);

CREATE TABLE trip_country_list (
    trip_country_id INT AUTO_INCREMENT PRIMARY KEY,
    trip_id INT NOT NULL,
    country_id INT NOT NULL,
    in_date DATE,
    out_date DATE,
    stayed_day INT,
    CONSTRAINT fk_trip_country_trip
        FOREIGN KEY (trip_id)
        REFERENCES trip_list(trip_id),
    CONSTRAINT fk_trip_country_country
        FOREIGN KEY (country_id)
        REFERENCES country_list(country_id)
);

CREATE TABLE trip_location_list (
    trip_location_id INT AUTO_INCREMENT PRIMARY KEY,
    trip_id INT NOT NULL,
    country_id INT NOT NULL,
    location_id INT NOT NULL,
    location_in DATE,
    location_out DATE,
    stayed_day INT,
    CONSTRAINT fk_trip_location_trip
        FOREIGN KEY (trip_id)
        REFERENCES trip_list(trip_id),
    CONSTRAINT fk_trip_location_country
        FOREIGN KEY (country_id)
        REFERENCES country_list(country_id),
    CONSTRAINT fk_trip_location_location
        FOREIGN KEY (location_id)
        REFERENCES location_list(location_id)
);

CREATE TABLE trip_country_score (
    country_score_id INT AUTO_INCREMENT PRIMARY KEY,
    trip_country_id INT NOT NULL,
    country_score INT,
    CONSTRAINT fk_country_score_trip_country
        FOREIGN KEY (trip_country_id)
        REFERENCES trip_country_list(trip_country_id)
);

CREATE TABLE trip_location_score (
    location_score_id INT AUTO_INCREMENT PRIMARY KEY,
    trip_location_id INT NOT NULL,
    location_score INT,
    CONSTRAINT fk_location_score_trip_location
        FOREIGN KEY (trip_location_id)
        REFERENCES trip_location_list(trip_location_id)
);

CREATE VIEW country_region_view AS
SELECT
    c.country_id,
    c.country_name,
    c.visit_status,
    c.visit_count,
    r.region_id,
    r.region_name
FROM country_list c
LEFT JOIN region_list r
    ON c.region_id = r.region_id;
