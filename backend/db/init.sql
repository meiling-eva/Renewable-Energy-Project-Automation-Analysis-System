-- For a local (non-Docker) MySQL install. Run with: mysql -u root < backend/db/init.sql
CREATE DATABASE IF NOT EXISTS automation_process CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'app_user'@'localhost' IDENTIFIED BY 'app_password';
CREATE USER IF NOT EXISTS 'app_user'@'127.0.0.1' IDENTIFIED BY 'app_password';
GRANT ALL PRIVILEGES ON automation_process.* TO 'app_user'@'localhost';
GRANT ALL PRIVILEGES ON automation_process.* TO 'app_user'@'127.0.0.1';
FLUSH PRIVILEGES;
