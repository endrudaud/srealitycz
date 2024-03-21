-- Create the docker schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS docker;

-- Create the sreality table
CREATE TABLE IF NOT EXISTS docker.sreality (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    image_url VARCHAR(255),
    page_number INTEGER
);
