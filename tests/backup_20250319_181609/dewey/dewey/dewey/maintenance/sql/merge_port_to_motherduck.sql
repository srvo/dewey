-- SQL to merge port database to MotherDuck
-- Generated on 2025-03-19 03:05:20

-- Create port_entity_analytics table from local entity_analytics
CREATE TABLE md:dewey.port_entity_analytics AS SELECT * FROM 'duckdb_temp/port.duckdb'.entity_analytics;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.port_entity_analytics;

-- Create port_fct_entity_analytics table from local fct_entity_analytics
CREATE TABLE md:dewey.port_fct_entity_analytics AS SELECT * FROM 'duckdb_temp/port.duckdb'.fct_entity_analytics;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.port_fct_entity_analytics;

-- Create port_int_entity_metrics table from local int_entity_metrics
CREATE TABLE md:dewey.port_int_entity_metrics AS SELECT * FROM 'duckdb_temp/port.duckdb'.int_entity_metrics;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.port_int_entity_metrics;

-- Create port_markdown_sections table from local markdown_sections
CREATE TABLE md:dewey.port_markdown_sections AS SELECT * FROM 'duckdb_temp/port.duckdb'.markdown_sections;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.port_markdown_sections;

-- Create port_stg_entity_analytics table from local stg_entity_analytics
CREATE TABLE md:dewey.port_stg_entity_analytics AS SELECT * FROM 'duckdb_temp/port.duckdb'.stg_entity_analytics;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.port_stg_entity_analytics;

-- Create port_temp_entities table from local temp_entities
CREATE TABLE md:dewey.port_temp_entities AS SELECT * FROM 'duckdb_temp/port.duckdb'.temp_entities;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.port_temp_entities;
