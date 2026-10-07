-- Adds projects.segment for databases created before the column existed.
-- Run with: mysql -u app_user -p automation_process < backend/db/migrations/001_add_project_segment.sql
ALTER TABLE projects
    ADD COLUMN segment ENUM('commercial', 'industrial') NULL AFTER system_type;
