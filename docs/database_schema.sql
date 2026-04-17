-- ==========================================================================
-- PRODUCTION MARIADB SCHEMA FOR AUTH MICROSERVICE
-- ==========================================================================
-- This schema follows Clean Architecture principles by maintaining a clear
-- separation between data persistence (Infrastructure) and business logic.
-- Each table maps to domain entities defined in your Python models.
-- ==========================================================================

-- Create the auth database if it doesn't exist
-- Note: In production, this should be executed by a database administrator
CREATE DATABASE IF NOT EXISTS `auth_db`
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

SELECT 'Database [auth_db] created successfully.' as Message;

-- Switch to the auth database
USE `auth_db`;

-- ==========================================================================
-- USER MANAGEMENT TABLES
-- ==========================================================================

-- Users table for authentication and authorization
-- Maps to: UserType and UserInDBType in user_models.py
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(100) NOT NULL UNIQUE,
    `email` VARCHAR(255) NULL,
    `ms_oid` VARCHAR(255) NULL UNIQUE,
    `full_name` VARCHAR(255) NULL,
    `first_name` VARCHAR(255) NULL,
    `last_name` VARCHAR(255) NULL,
    `hashed_password` VARCHAR(500) NOT NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `manager` INT NULL,
    `unit` VARCHAR(255) NULL,
    `job` VARCHAR(255) NULL,
    `branche` VARCHAR(255) NULL,
    `cpf_cnpj` VARCHAR(20) NULL,
    `registration_number` VARCHAR(50) NULL,
    `profile_picture_url` VARCHAR(1000) NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX `idx_users_username` (`username`),
    INDEX `idx_users_email` (`email`),
    INDEX `idx_users_registration` (`registration_number`)
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

SELECT 'Table [users] created successfully.' as Message;

CREATE TABLE IF NOT EXISTS `departments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `erp_id` VARCHAR(255) NOT NULL UNIQUE,
    `name` VARCHAR(255) NOT NULL UNIQUE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

SELECT 'Table [departments] created successfully.' as Message;

CREATE TABLE IF NOT EXISTS `positions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `erp_id` VARCHAR(255) NOT NULL UNIQUE,
    `name` VARCHAR(255) NOT NULL UNIQUE,
    `department_id` INT NOT NULL,
    `branch` VARCHAR(255) NOT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

SELECT 'Table [positions] created successfully.' as Message;


-- Applications table for storing system-related URLs
-- Maps to: Applications model in models.py
CREATE TABLE IF NOT EXISTS `applications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(255) NOT NULL,
    `uri` VARCHAR(1000) NOT NULL,
    `type` VARCHAR(100) NOT NULL, -- e.g., 'all', 'internal', 'external'
    `description` VARCHAR(500) DEFAULT NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Index for URI lookup
    INDEX `idx_applications_name` (`name`)
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

SELECT 'Table [applications] created successfully.' as Message;


-- ==========================================================================
-- TOKEN MANAGEMENT TABLES
-- ==========================================================================

-- Tokens table for access and refresh tokens
-- Maps to: TokenModel in oauth_models.py
CREATE TABLE IF NOT EXISTS `tokens` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `token` TEXT NOT NULL,
    `type` ENUM('access', 'refresh') NOT NULL,
    `parent_token` TEXT NULL, -- References the token that generated this one
    `revoked` BOOLEAN DEFAULT FALSE,
    `consumed_at` DATETIME NULL,
    `expires_at` DATETIME NOT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign key constraint
    CONSTRAINT `fk_tokens_user` FOREIGN KEY (`user_id`)
        REFERENCES `users`(`id`) ON DELETE CASCADE,
        
    -- Indexes for performance
    INDEX `idx_tokens_user_id` (`user_id`),
    INDEX `idx_tokens_expires` (`expires_at`),
    INDEX `idx_tokens_type` (`type`)
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

SELECT 'Table [tokens] created successfully.' as Message;


CREATE TABLE IF NOT EXISTS `user_applications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `application_id` INT NOT NULL,
    `permissions` JSON NOT NULL, -- Object with permissions of user in application | {"read": "read", "write": "write", "delete": "delete", "denied": "denied"}
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT `fk_user_applications_user` FOREIGN KEY (`user_id`)
        REFERENCES `users`(`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_applications_application` FOREIGN KEY (`application_id`)
        REFERENCES `applications`(`id`) ON DELETE CASCADE,
        
    -- Indexes for performance
    INDEX `idx_user_applications_user_id` (`user_id`),
    INDEX `idx_user_applications_application_id` (`application_id`)
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

SELECT 'Table [user_applications] created successfully.' as Message;


-- ==========================================================================
-- AUDIT AND LOGGING TABLES
-- ==========================================================================

-- Audit log for tracking system changes
CREATE TABLE IF NOT EXISTS `database_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `operation_type` VARCHAR(50) NOT NULL, -- 'LOGIN', 'READ', 'INSERT', 'UPDATE', 'DELETE'
    `table_name` VARCHAR(255) NOT NULL,
    `timestamp` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `user_id` INT NULL,
    `details` TEXT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign key constraint
    CONSTRAINT `fk_database_logs_user` FOREIGN KEY (`user_id`)
        REFERENCES `users`(`id`) ON DELETE SET NULL,
        
    -- Indexes for performance
    INDEX `idx_database_logs_table_name` (`table_name`),
    INDEX `idx_database_logs_timestamp` (`timestamp`)
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

SELECT 'Table [database_logs] created successfully.' as Message;

-- ==========================================================================
-- INITIAL DATA SETUP
-- ==========================================================================

-- Create default admin user (in production, this should be done securely)
-- This follows the Dependency Inversion Principle by not hardcoding credentials
-- The actual password should be injected via environment variables

-- Note: This is commented out for security reasons in production
-- Uncomment and modify as needed for your initial setup

-- INSERT IGNORE INTO `users` (`username`, `email`, `full_name`, `first_name`, `last_name`, `manager`, `unit`, `job`, `branche`, `cpf_cnpj`, `registration_number`, `profile_picture_url`, `hashed_password`, `is_active`)
-- VALUES ('administrador', 'admin@pedreiraumvalemix.com.br', 'Administrator do Sistema', 'Administrator', 'do Sistema', NULL, NULL, NULL, NULL, '99999999999', '99999999999', NULL, '$2b$12$XmebKoVqAqEHbnh.8qdnQehrdxKR2Y9MqYblvyWGyqNQN6c16wkRK', TRUE);

-- SELECT 'Default admin user created. Please update the password hash!' as Message;

-- ==========================================================================
-- PERFORMANCE OPTIMIZATION
-- ==========================================================================

-- Analyze tables for optimal query performance in MariaDB
ANALYZE TABLE `users`, `tokens`, `applications`;

SELECT 'Database statistics updated for optimal performance.' as Message;

-- ==========================================================================
-- COMPLETION MESSAGE
-- ==========================================================================

SELECT '==========================================' as Message;
SELECT 'AUTH MICROSERVICE PRODUCTION SCHEMA SETUP COMPLETE' as Message;
SELECT '==========================================' as Message;
SELECT 'All tables, indexes, and constraints have been created successfully.' as Message;
SELECT 'Remember to:' as Message;
SELECT '1. Set up proper backup procedures' as Message;
SELECT '2. Configure appropriate user permissions' as Message;
SELECT '3. Update connection strings in your application' as Message;
SELECT '4. Test all database operations' as Message;
SELECT '==========================================' as Message;