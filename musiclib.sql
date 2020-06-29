SET NAMES utf8;
SET time_zone = '+00:00';
SET foreign_key_checks = 0;
SET sql_mode = 'NO_AUTO_VALUE_ON_ZERO';

SET NAMES utf8mb4;

CREATE TABLE `albums` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` text NOT NULL,
  `release_date` date DEFAULT NULL,
  `artist` text NOT NULL,
  `format` varchar(20) NOT NULL,
  `quality` varchar(20) NOT NULL,
  `quality_details` varchar(50) NOT NULL,
  `source` text NOT NULL,
  `file_source` text NOT NULL,
  `trusted` tinyint(1) NOT NULL DEFAULT 0,
  `log_files` text NOT NULL,
  `cover_files` text NOT NULL,
  `comments` text NOT NULL,
  `extra_data` mediumtext NOT NULL DEFAULT '{}',
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4;


CREATE TABLE `albums_files` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `album_id` int(11) NOT NULL,
  `name` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `file` text COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE `files` (
  `sha512` binary(64) NOT NULL,
  `count` int(11) NOT NULL,
  PRIMARY KEY (`sha512`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE `playlists` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `tracklist` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_update` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `last_update` (`last_update`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE `scans` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` text NOT NULL,
  `album_id` int(11) NOT NULL,
  `files` text NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4;


CREATE TABLE `songs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `album_id` int(11) NOT NULL,
  `track` int(11) NOT NULL,
  `title` text NOT NULL,
  `artist` text NOT NULL,
  `duration` varchar(8) NOT NULL,
  `format` varchar(20) NOT NULL,
  `quality` varchar(20) NOT NULL,
  `quality_details` varchar(50) NOT NULL,
  `file` text NOT NULL,
  `file_flac` text NOT NULL,
  `extra_data` mediumtext NOT NULL DEFAULT '{}',
  PRIMARY KEY (`id`),
  KEY `album_id_track` (`album_id`,`track`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4;
