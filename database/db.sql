-- FoodBridge Database Schema

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    user_type TEXT NOT NULL CHECK(user_type IN ('hotel', 'ngo')),
    phone TEXT,
    address TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS food_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hotel_id INTEGER NOT NULL,
    food_name TEXT NOT NULL,
    category TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit TEXT NOT NULL,
    food_type TEXT NOT NULL CHECK(food_type IN ('veg', 'nonveg', 'vegan')),
    prepared_at TEXT,
    best_before TEXT NOT NULL,
    pickup_address TEXT NOT NULL,
    instructions TEXT,
    contact_name TEXT,
    contact_phone TEXT,
    allergens TEXT,
    is_claimed INTEGER DEFAULT 0,
    ngo_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hotel_id) REFERENCES users(id),
    FOREIGN KEY (ngo_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS food_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    food_id INTEGER NOT NULL,
    ngo_id INTEGER NOT NULL,
    people_count INTEGER DEFAULT 0,
    pickup_eta TEXT,
    message TEXT,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'completed')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (food_id) REFERENCES food_listings(id),
    FOREIGN KEY (ngo_id) REFERENCES users(id)
);

-- Sample data for testing
INSERT OR IGNORE INTO users (name, email, password, user_type, phone, address)
VALUES 
    ('Grand Palace Hotel', 'hotel@test.com', 'test123', 'hotel', '9876543210', '42 MG Road, Kochi'),
    ('Hope Foundation', 'ngo@test.com', 'test123', 'ngo', '9123456789', '15 Church Street, Kochi');