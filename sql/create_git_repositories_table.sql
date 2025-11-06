-- SQL script to create the git_repositories table
-- This can be used to manually create the table if needed

CREATE TABLE IF NOT EXISTS `git_repositories` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `region` varchar(50) NOT NULL,
  `web_url` varchar(512) NOT NULL,
  `https_url` varchar(512) DEFAULT NULL,
  `ssh_url` varchar(512) DEFAULT NULL,
  `type` varchar(50) DEFAULT NULL,
  `token` varchar(512) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uix_name_region` (`name`, `region`),
  KEY `ix_git_repositories_id` (`id`),
  KEY `ix_git_repositories_name` (`name`),
  KEY `ix_git_repositories_region` (`region`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
