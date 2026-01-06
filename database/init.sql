-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Create tables
CREATE TABLE IF NOT EXISTS core_user (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE,
    is_superuser BOOLEAN NOT NULL DEFAULT false,
    username VARCHAR(150) UNIQUE NOT NULL,
    first_name VARCHAR(150) NOT NULL DEFAULT '',
    last_name VARCHAR(150) NOT NULL DEFAULT '',
    email VARCHAR(254) UNIQUE NOT NULL,
    is_staff BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    date_joined TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    phone_number VARCHAR(15) UNIQUE NOT NULL,
    profile_image VARCHAR(100),
    is_verified BOOLEAN NOT NULL DEFAULT false,
    verification_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    location GEOGRAPHY(POINT, 4326),
    current_pincode VARCHAR(10),
    address TEXT,
    rating DOUBLE PRECISION NOT NULL DEFAULT 0.0 CHECK (rating >= 0 AND rating <= 5),
    total_transactions INTEGER NOT NULL DEFAULT 0,
    id_proof_front VARCHAR(100),
    id_proof_back VARCHAR(100),
    address_proof VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS core_pincodeboundary (
    id SERIAL PRIMARY KEY,
    pincode VARCHAR(10) UNIQUE NOT NULL,
    boundary GEOGRAPHY(POLYGON, 4326) NOT NULL,
    center_point GEOGRAPHY(POINT, 4326) NOT NULL,
    area_name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    state VARCHAR(50) NOT NULL,
    population INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS core_servicecategory (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    icon VARCHAR(50) NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS core_service (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID NOT NULL REFERENCES core_user(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    category_id INTEGER REFERENCES core_servicecategory(id) ON DELETE SET NULL,
    service_type VARCHAR(20) NOT NULL,
    price_per_hour DECIMAL(10, 2),
    price_per_day DECIMAL(10, 2),
    price_per_unit DECIMAL(10, 2),
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    pincode VARCHAR(10) NOT NULL,
    address TEXT NOT NULL,
    is_available BOOLEAN NOT NULL DEFAULT true,
    available_from TIME,
    available_to TIME,
    average_rating DOUBLE PRECISION NOT NULL DEFAULT 0.0 CHECK (average_rating >= 0 AND average_rating <= 5),
    total_bookings INTEGER NOT NULL DEFAULT 0,
    images JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS core_booking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID NOT NULL REFERENCES core_service(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES core_user(id) ON DELETE CASCADE,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    total_hours INTEGER,
    total_days INTEGER,
    total_amount DECIMAL(10, 2) NOT NULL,
    platform_fee DECIMAL(10, 2) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    payment_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    razorpay_order_id VARCHAR(100),
    razorpay_payment_id VARCHAR(100),
    user_rating DOUBLE PRECISION CHECK (user_rating >= 0 AND user_rating <= 5),
    provider_rating DOUBLE PRECISION CHECK (provider_rating >= 0 AND provider_rating <= 5),
    user_review TEXT,
    provider_review TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS core_chatroom (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user1_id UUID NOT NULL REFERENCES core_user(id) ON DELETE CASCADE,
    user2_id UUID NOT NULL REFERENCES core_user(id) ON DELETE CASCADE,
    last_message TEXT,
    last_message_time TIMESTAMP WITH TIME ZONE,
    unread_count_user1 INTEGER NOT NULL DEFAULT 0,
    unread_count_user2 INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user1_id, user2_id)
);

CREATE TABLE IF NOT EXISTS core_message (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID NOT NULL REFERENCES core_chatroom(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES core_user(id) ON DELETE CASCADE,
    receiver_id UUID NOT NULL REFERENCES core_user(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    message_type VARCHAR(20) NOT NULL DEFAULT 'text',
    is_read BOOLEAN NOT NULL DEFAULT false,
    read_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_location ON core_user USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_user_pincode ON core_user(current_pincode);
CREATE INDEX IF NOT EXISTS idx_user_phone ON core_user(phone_number);
CREATE INDEX IF NOT EXISTS idx_user_email ON core_user(email);

CREATE INDEX IF NOT EXISTS idx_pincode_boundary ON core_pincodeboundary USING GIST(boundary);
CREATE INDEX IF NOT EXISTS idx_pincode_code ON core_pincodeboundary(pincode);

CREATE INDEX IF NOT EXISTS idx_service_location ON core_service USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_service_pincode ON core_service(pincode);
CREATE INDEX IF NOT EXISTS idx_service_provider ON core_service(provider_id);
CREATE INDEX IF NOT EXISTS idx_service_available ON core_service(is_available);
CREATE INDEX IF NOT EXISTS idx_service_category ON core_service(category_id);

CREATE INDEX IF NOT EXISTS idx_booking_service ON core_booking(service_id);
CREATE INDEX IF NOT EXISTS idx_booking_user ON core_booking(user_id);
CREATE INDEX IF NOT EXISTS idx_booking_status ON core_booking(status);
CREATE INDEX IF NOT EXISTS idx_booking_created ON core_booking(created_at);

CREATE INDEX IF NOT EXISTS idx_chatroom_user1 ON core_chatroom(user1_id);
CREATE INDEX IF NOT EXISTS idx_chatroom_user2 ON core_chatroom(user2_id);
CREATE INDEX IF NOT EXISTS idx_chatroom_updated ON core_chatroom(updated_at);

CREATE INDEX IF NOT EXISTS idx_message_room ON core_message(room_id);
CREATE INDEX IF NOT EXISTS idx_message_sender ON core_message(sender_id);
CREATE INDEX IF NOT EXISTS idx_message_receiver ON core_message(receiver_id);
CREATE INDEX IF NOT EXISTS idx_message_created ON core_message(created_at);

-- Insert sample categories
INSERT INTO core_servicecategory (name, description, icon) VALUES
('Tools & Equipment', 'Power tools, hand tools, gardening equipment', 'build'),
('Books & Media', 'Books, magazines, movies, music', 'book'),
('Electronics', 'Gadgets, appliances, audio equipment', 'devices'),
('Home & Kitchen', 'Cookware, appliances, furniture', 'kitchen'),
('Sports & Fitness', 'Exercise equipment, sports gear', 'fitness_center'),
('Vehicles', 'Cars, bikes, scooters for rent', 'directions_car'),
('Skills & Services', 'Professional services, tutoring, repairs', 'handyman'),
('Fashion & Accessories', 'Clothing, jewelry, accessories', 'checkroom'),
('Toys & Games', 'Children toys, board games, video games', 'toys'),
('Miscellaneous', 'Other items and services', 'category')
ON CONFLICT DO NOTHING;

-- Create sample pincode boundaries (Delhi area)
INSERT INTO core_pincodeboundary (
    pincode,
    boundary,
    center_point,
    area_name,
    city,
    state
) VALUES (
    '110001',
    ST_GeomFromText('POLYGON((77.2090 28.6324, 77.2120 28.6340, 77.2150 28.6320, 77.2130 28.6300, 77.2090 28.6324))', 4326),
    ST_GeomFromText('POINT(77.2120 28.6322)', 4326),
    'Connaught Place',
    'New Delhi',
    'Delhi'
),
(
    '110002',
    ST_GeomFromText('POLYGON((77.2050 28.6350, 77.2080 28.6370, 77.2100 28.6340, 77.2070 28.6320, 77.2050 28.6350))', 4326),
    ST_GeomFromText('POINT(77.2075 28.6345)', 4326),
    'Shivaji Stadium',
    'New Delhi',
    'Delhi'
)
ON CONFLICT (pincode) DO NOTHING;

-- Create function to update service rating
CREATE OR REPLACE FUNCTION update_service_rating()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.user_rating IS NOT NULL THEN
        UPDATE core_service
        SET average_rating = (
            SELECT AVG(user_rating)
            FROM core_booking
            WHERE service_id = NEW.service_id
            AND user_rating IS NOT NULL
        )
        WHERE id = NEW.service_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER booking_rating_trigger
AFTER UPDATE OF user_rating ON core_booking
FOR EACH ROW
EXECUTE FUNCTION update_service_rating();

-- Create function to update user rating
CREATE OR REPLACE FUNCTION update_user_rating()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.user_rating IS NOT NULL OR NEW.provider_rating IS NOT NULL THEN
        -- Update user rating (as customer)
        UPDATE core_user
        SET rating = (
            SELECT AVG(user_rating)
            FROM core_booking
            WHERE user_id = NEW.user_id
            AND user_rating IS NOT NULL
        )
        WHERE id = NEW.user_id;
        
        -- Update provider rating
        UPDATE core_user u
        SET rating = (
            SELECT AVG(provider_rating)
            FROM core_booking b
            JOIN core_service s ON b.service_id = s.id
            WHERE s.provider_id = u.id
            AND provider_rating IS NOT NULL
        )
        FROM core_service s
        WHERE s.id = NEW.service_id
        AND u.id = s.provider_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_rating_trigger
AFTER UPDATE OF user_rating, provider_rating ON core_booking
FOR EACH ROW
EXECUTE FUNCTION update_user_rating();

-- Create function to check distance between users
CREATE OR REPLACE FUNCTION check_user_distance(
    user1_id UUID,
    user2_id UUID,
    max_distance_km FLOAT DEFAULT 1.5
)
RETURNS BOOLEAN AS $$
DECLARE
    user1_location GEOGRAPHY;
    user2_location GEOGRAPHY;
    distance_meters FLOAT;
BEGIN
    SELECT location INTO user1_location FROM core_user WHERE id = user1_id;
    SELECT location INTO user2_location FROM core_user WHERE id = user2_id;
    
    IF user1_location IS NULL OR user2_location IS NULL THEN
        RETURN FALSE;
    END IF;
    
    distance_meters = ST_Distance(user1_location, user2_location);
    
    RETURN (distance_meters / 1000) <= max_distance_km;
END;
$$ LANGUAGE plpgsql;
