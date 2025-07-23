
-- Database schema for MySQL migration
CREATE DATABASE IF NOT EXISTS debate_system;
USE debate_system;

CREATE TABLE users (
    id VARCHAR(32) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL,
    player_name VARCHAR(100),
    is_admin BOOLEAN DEFAULT FALSE,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    approved BOOLEAN DEFAULT TRUE
);

CREATE TABLE players (
    name VARCHAR(100) PRIMARY KEY,
    elo INT DEFAULT 1200,
    formats JSON,
    matches_won INT DEFAULT 0,
    matches_lost INT DEFAULT 0,
    total_matches INT DEFAULT 0,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE teams (
    name VARCHAR(100) PRIMARY KEY,
    members JSON,
    elo INT DEFAULT 1200,
    format VARCHAR(10),
    matches_won INT DEFAULT 0,
    matches_lost INT DEFAULT 0,
    total_matches INT DEFAULT 0,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE matches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type VARCHAR(10),
    participants JSON,
    winner_data JSON,
    loser_data JSON,
    elo_changes JSON,
    date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE settings (
    setting_key VARCHAR(50) PRIMARY KEY,
    setting_value JSON
);

CREATE TABLE forum_posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    author VARCHAR(50),
    content TEXT,
    date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255),
    content TEXT,
    author VARCHAR(50),
    date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rubrics (
    id VARCHAR(16) PRIMARY KEY,
    title VARCHAR(255),
    description TEXT,
    criteria TEXT,
    created_by VARCHAR(50),
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE practice_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    topic TEXT,
    user_position VARCHAR(10),
    ai_position VARCHAR(10),
    user_argument TEXT,
    ai_response TEXT,
    format VARCHAR(10),
    user VARCHAR(50),
    date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE banned_users (
    user_id VARCHAR(32) PRIMARY KEY,
    until DATETIME,
    reason TEXT,
    banned_by VARCHAR(32),
    banned_date DATETIME DEFAULT CURRENT_TIMESTAMP
);
