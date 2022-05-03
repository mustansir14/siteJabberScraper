CREATE DATABASE IF NOT EXISTS site_jabber;

CREATE TABLE IF NOT EXISTS `company` (
  `company_id` varchar(255) NOT NULL,
  `company_name` varchar(255) NOT NULL,
  `url` varchar(500) NOT NULL,
  `logo` varchar(255) DEFAULT NULL,
  `category1` varchar(255) DEFAULT NULL,
  `category2` varchar(255) DEFAULT NULL,
  `category3` varchar(255) DEFAULT NULL,
  `email` varchar(320) DEFAULT NULL,
  `phone` varchar(18) DEFAULT NULL,
  `street_address1` varchar(255) DEFAULT NULL,
  `street_address2` varchar(255) DEFAULT NULL,
  `city` varchar(255) DEFAULT NULL,
  `state` varchar(255) DEFAULT NULL,
  `zip_code` varchar(255) DEFAULT NULL,
  `country` varchar(255) DEFAULT NULL,
  `wikipedia_url` varchar(500) DEFAULT NULL,
  `facebook_url` varchar(500) DEFAULT NULL,
  `twitter_url` varchar(500) DEFAULT NULL,
  `linkedin_url` varchar(500) DEFAULT NULL,
  `youtube_url` varchar(500) DEFAULT NULL,
  `pinterest_url` varchar(500) DEFAULT NULL,
  `instagram_url` varchar(500) DEFAULT NULL,
  `description` text default null,
  `date_created` datetime DEFAULT NULL,
  `date_updated` datetime DEFAULT NULL,
  `status` varchar(7) DEFAULT NULL,
  `log` varchar(255) DEFAULT NULL,
  `wiki_info` longtext DEFAULT NULL,
  `bbb_url` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`company_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci


CREATE TABLE IF NOT EXISTS `review` (
  `review_id` int NOT NULL AUTO_INCREMENT,
  `company_id` varchar(255) NOT NULL,
  `review_date` date DEFAULT NULL,
  `username` varchar(255) NOT NULL,
  `no_of_helpful_votes` int NOT NULL,
  `review_title` varchar(255) NOT NULL,
  `review_text` text,
  `review_stars` decimal(2,1) DEFAULT NULL,
  `review_page_no` int DEFAULT NULL,
  `date_created` datetime DEFAULT NULL,
  `date_updated` datetime DEFAULT NULL,
  `status` varchar(7) DEFAULT NULL,
  `log` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`review_id`),
  KEY `company_id` (`company_id`),
  CONSTRAINT `review_ibfk_1` FOREIGN KEY (`company_id`) REFERENCES `company` (`company_id`)
) ENGINE=InnoDB AUTO_INCREMENT=78366 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
