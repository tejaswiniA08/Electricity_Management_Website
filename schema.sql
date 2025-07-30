-- Create the users table
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fullname TEXT NOT NULL,
  username TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  password TEXT NOT NULL,
  type TEXT
);