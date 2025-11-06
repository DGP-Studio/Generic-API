-- Migration script to add region support to git_repositories table
-- This migration adds the region column and updates the unique constraint

-- Step 1: Add region column with default value 'cn'
-- (existing records will get 'cn' as their region)
ALTER TABLE git_repositories 
ADD COLUMN region VARCHAR(50) NOT NULL DEFAULT 'cn';

-- Step 2: Add index on region column
ALTER TABLE git_repositories 
ADD INDEX ix_git_repositories_region (region);

-- Step 3: Drop old unique constraint on name only
ALTER TABLE git_repositories 
DROP INDEX name;

-- Step 4: Add new composite unique constraint on (name, region)
ALTER TABLE git_repositories 
ADD UNIQUE KEY uix_name_region (name, region);

-- After running this migration:
-- 1. All existing repositories will have region='cn'
-- 2. You can now create repositories with the same name but different regions
-- 3. Each (name, region) combination must be unique
