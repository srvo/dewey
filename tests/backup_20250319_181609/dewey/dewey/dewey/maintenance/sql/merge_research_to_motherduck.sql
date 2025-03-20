-- SQL to merge research database to MotherDuck
-- Generated on 2025-03-19 03:05:20

-- Create research_company_context table from local company_context
CREATE TABLE md:dewey.research_company_context AS SELECT * FROM 'duckdb_temp/research.duckdb'.company_context;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.research_company_context;

-- Create research_current_universe table from local current_universe
CREATE TABLE md:dewey.research_current_universe AS SELECT * FROM 'duckdb_temp/research.duckdb'.current_universe;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.research_current_universe;

-- Create research_exclusions table from local exclusions
CREATE TABLE md:dewey.research_exclusions AS SELECT * FROM 'duckdb_temp/research.duckdb'.exclusions;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.research_exclusions;

-- Create research_podcast_episodes table from local podcast_episodes
CREATE TABLE md:dewey.research_podcast_episodes AS SELECT * FROM 'duckdb_temp/research.duckdb'.podcast_episodes;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.research_podcast_episodes;

-- Create research_portfolio table from local portfolio
CREATE TABLE md:dewey.research_portfolio AS SELECT * FROM 'duckdb_temp/research.duckdb'.portfolio;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.research_portfolio;

-- Create research_research table from local research
CREATE TABLE md:dewey.research_research AS SELECT * FROM 'duckdb_temp/research.duckdb'.research;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.research_research;

-- Create research_research_iterations table from local research_iterations
CREATE TABLE md:dewey.research_research_iterations AS SELECT * FROM 'duckdb_temp/research.duckdb'.research_iterations;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.research_research_iterations;

-- Create research_research_results table from local research_results
CREATE TABLE md:dewey.research_research_results AS SELECT * FROM 'duckdb_temp/research.duckdb'.research_results;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.research_research_results;

-- Create research_research_reviews table from local research_reviews
CREATE TABLE md:dewey.research_research_reviews AS SELECT * FROM 'duckdb_temp/research.duckdb'.research_reviews;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.research_research_reviews;

-- Create research_research_sources table from local research_sources
CREATE TABLE md:dewey.research_research_sources AS SELECT * FROM 'duckdb_temp/research.duckdb'.research_sources;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.research_research_sources;

-- Create research_test_table table from local test_table
CREATE TABLE md:dewey.research_test_table AS SELECT * FROM 'duckdb_temp/research.duckdb'.test_table;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.research_test_table;

-- Create research_universe table from local universe
CREATE TABLE md:dewey.research_universe AS SELECT * FROM 'duckdb_temp/research.duckdb'.universe;
-- Row count verification
SELECT COUNT(*) FROM md:dewey.research_universe;
