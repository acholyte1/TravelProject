# 데이터베이스 구조

## 개요

- 데이터베이스: `mytripdb`
- DBMS: MySQL
- 기준 파일: `migrations/000_init_schema.sql`
- 테이블: 7개
- 뷰: 1개

## `region_list`

지역 정보를 관리한다.

| 컬럼 | 타입 | NULL | 키/제약 | 기본값 |
| --- | --- | --- | --- | --- |
| `region_id` | `INT` | 불가 | PK, AUTO_INCREMENT | - |
| `region_name` | `VARCHAR(100)` | 불가 | - | - |

## `country_list`

국가와 방문 상태를 관리한다.

| 컬럼 | 타입 | NULL | 키/제약 | 기본값 |
| --- | --- | --- | --- | --- |
| `country_id` | `INT` | 불가 | PK, AUTO_INCREMENT | - |
| `country_name` | `VARCHAR(100)` | 불가 | UNIQUE | - |
| `visit_status` | `VARCHAR(20)` | 가능 | - | `NULL` |
| `visit_count` | `INT` | 가능 | - | `0` |
| `region_id` | `INT` | 가능 | FK -> `region_list.region_id` | `NULL` |

애플리케이션은 국가명을 저장하기 전에 앞뒤 공백을 제거한다. 기존 DB에는 `migrations/003_add_unique_country_name.sql`을 적용해야 `UNIQUE` 제약이 반영된다.

## `location_list`

국가에 속한 도시 또는 여행지 정보를 관리한다.

| 컬럼 | 타입 | NULL | 키/제약 | 기본값 |
| --- | --- | --- | --- | --- |
| `location_id` | `INT` | 불가 | PK, AUTO_INCREMENT | - |
| `country_id` | `INT` | 불가 | FK -> `country_list.country_id` | - |
| `location_name` | `VARCHAR(100)` | 불가 | - | - |
| `visit_status` | `VARCHAR(20)` | 가능 | - | `NULL` |
| `visit_count` | `INT` | 가능 | - | `0` |
| `region_id` | `INT` | 가능 | FK -> `region_list.region_id` | `NULL` |

## `trip_list`

여행의 전체 기간과 삭제 상태를 관리한다.

| 컬럼 | 타입 | NULL | 키/제약 | 기본값 |
| --- | --- | --- | --- | --- |
| `trip_id` | `INT` | 불가 | PK, AUTO_INCREMENT | - |
| `in_date` | `DATE` | 가능 | - | `NULL` |
| `out_date` | `DATE` | 가능 | - | `NULL` |
| `stayed_day` | `INT` | 가능 | - | `NULL` |
| `is_deleted` | `TINYINT` | 가능 | - | `0` |

## `trip_country_list`

여행과 방문 국가를 연결하고 국가별 체류 기간을 관리한다.

| 컬럼 | 타입 | NULL | 키/제약 | 기본값 |
| --- | --- | --- | --- | --- |
| `trip_country_id` | `INT` | 불가 | PK, AUTO_INCREMENT | - |
| `trip_id` | `INT` | 불가 | FK -> `trip_list.trip_id` | - |
| `country_id` | `INT` | 불가 | FK -> `country_list.country_id` | - |
| `in_date` | `DATE` | 가능 | - | `NULL` |
| `out_date` | `DATE` | 가능 | - | `NULL` |
| `stayed_day` | `INT` | 가능 | - | `NULL` |

## `trip_location_list`

여행과 방문 도시 또는 여행지를 연결하고 장소별 체류 기간을 관리한다.

| 컬럼 | 타입 | NULL | 키/제약 | 기본값 |
| --- | --- | --- | --- | --- |
| `trip_location_id` | `INT` | 불가 | PK, AUTO_INCREMENT | - |
| `trip_id` | `INT` | 불가 | FK -> `trip_list.trip_id` | - |
| `country_id` | `INT` | 불가 | FK -> `country_list.country_id` | - |
| `location_id` | `INT` | 불가 | FK -> `location_list.location_id` | - |
| `location_in` | `DATE` | 가능 | - | `NULL` |
| `location_out` | `DATE` | 가능 | - | `NULL` |

## `trip_country_score`

여행에서 방문한 국가의 점수를 관리한다.

| 컬럼 | 타입 | NULL | 키/제약 | 기본값 |
| --- | --- | --- | --- | --- |
| `country_score_id` | `INT` | 불가 | PK, AUTO_INCREMENT | - |
| `trip_country_id` | `INT` | 불가 | FK -> `trip_country_list.trip_country_id` | - |
| `country_score` | `INT` | 가능 | - | `NULL` |

## `trip_location_score`

여행에서 방문한 도시 또는 여행지의 점수를 관리한다.

| 컬럼 | 타입 | NULL | 키/제약 | 기본값 |
| --- | --- | --- | --- | --- |
| `location_score_id` | `INT` | 불가 | PK, AUTO_INCREMENT | - |
| `trip_location_id` | `INT` | 불가 | FK -> `trip_location_list.trip_location_id` | - |
| `location_score` | `INT` | 가능 | - | `NULL` |

## `country_region_view`

국가 목록 화면에서 국가와 지역 정보를 함께 조회하기 위한 뷰다.

| 출력 컬럼 | 원본 |
| --- | --- |
| `country_id` | `country_list.country_id` |
| `country_name` | `country_list.country_name` |
| `visit_status` | `country_list.visit_status` |
| `visit_count` | `country_list.visit_count` |
| `region_id` | `region_list.region_id` |
| `region_name` | `region_list.region_name` |

`country_list`와 `region_list`는 `LEFT JOIN`으로 연결된다.

## 마이그레이션 상태

| 파일 | 내용 | 저장소 기준 상태 |
| --- | --- | --- |
| `000_init_schema.sql` | 신규 DB 전체 구조 생성 | 기준 스키마 |
| `001_alter_trip_id_auto_increment.sql` | `trip_id` 자동 증가 보정 | 2026-06-10 수동 적용 기록 |
| `002_alter_visit_status_enum.sql` | 국가 및 여행지 방문 상태를 `ENUM`으로 제한 | 적용 예정 |
| `003_add_unique_country_name.sql` | 국가명 공백 정리 및 `UNIQUE` 제약 추가 | 적용 예정 |

`002`가 적용되면 `country_list.visit_status`와 `location_list.visit_status` 타입은 `ENUM('TRIP', 'STAY', 'WANT')`으로 변경된다. 실제 운영 DB의 적용 여부는 DB에서 별도로 확인해야 한다.
