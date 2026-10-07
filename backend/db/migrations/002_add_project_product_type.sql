-- Adds projects.product_type (PV or PV + Battery). Run after 001_add_project_segment.sql.
-- Run with: mysql -u app_user -p automation_process < backend/db/migrations/002_add_project_product_type.sql
ALTER TABLE projects
    ADD COLUMN product_type ENUM('pv', 'pv_battery') NULL AFTER segment;
