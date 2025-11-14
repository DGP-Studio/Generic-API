-- Migration script to remove unique constraint on (name, region) from git_repositories table
-- This allows multiple repositories with the same name in the same region

-- Drop the unique constraint on (name, region)
ALTER TABLE git_repositories 
DROP INDEX uix_name_region;

-- After running this migration:
-- 1. Multiple repositories can have the same name within the same region
-- 2. Repositories are uniquely identified by their ID only
-- 3. The name and region columns remain indexed for query performance
