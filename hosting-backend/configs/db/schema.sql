CREATE TABLE sites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    domain VARCHAR(255),
    path VARCHAR(255),
    db_name VARCHAR(100),
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);