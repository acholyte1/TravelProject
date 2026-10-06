-- 읽기 전용: DBeaver에서 실행 후 결과를 CSV로 내보내면 기존 기록과 대조할 수 있습니다.
SELECT trip_id, trip_name, trip_memo, in_date, out_date, stayed_day
FROM trip_list WHERE is_deleted = 0 ORDER BY in_date, trip_id;
SELECT tc.trip_country_id, tc.trip_id, t.trip_name, tc.country_id,
       c.country_name, c.country_name_ko, tc.in_date, tc.out_date
FROM trip_country_list tc JOIN trip_list t ON t.trip_id = tc.trip_id
JOIN country_list c ON c.country_id = tc.country_id
WHERE t.is_deleted = 0 ORDER BY tc.trip_id, tc.in_date;
SELECT tl.trip_location_id, tl.trip_id, t.trip_name, tl.country_id,
       c.country_name, tl.location_id, l.location_name, l.location_name_ko,
       tl.location_in, tl.location_out
FROM trip_location_list tl JOIN trip_list t ON t.trip_id = tl.trip_id
JOIN country_list c ON c.country_id = tl.country_id
JOIN location_list l ON l.location_id = tl.location_id
WHERE t.is_deleted = 0 ORDER BY tl.trip_id, tl.location_in;
SELECT country_id, country_name, country_name_ko, visit_status FROM country_list ORDER BY country_id;
SELECT location_id, country_id, location_name, location_name_ko, visit_status FROM location_list ORDER BY country_id, location_id;
