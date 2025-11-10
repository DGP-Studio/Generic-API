-- SQL migration script to add username column to git_repositories table
-- This adds the username field to track the repository owner/username

ALTER TABLE `git_repositories` 
ADD COLUMN `username` varchar(255) DEFAULT NULL;
