-- SQL to merge ecic database to MotherDuck
-- Generated on 2025-03-19 03:05:20

-- Create ecic_current_universe table from local current_universe
CREATE TABLE md:dewey.ecic_current_universe AS SELECT * FROM 'duckdb_temp/ecic.duckdb'.current_universe;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.ecic_current_universe;

-- Create ecic_tick_history table from local tick_history
CREATE TABLE md:dewey.ecic_tick_history AS SELECT * FROM 'duckdb_temp/ecic.duckdb'.tick_history;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.ecic_tick_history;
