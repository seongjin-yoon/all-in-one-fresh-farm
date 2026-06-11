CREATE TABLE IF NOT EXISTS rag_documents (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    source_path VARCHAR(512) NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1024) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_source_chunk (source_path, chunk_index),
    VECTOR INDEX (embedding) M=8 DISTANCE=cosine
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(128) NOT NULL DEFAULT 'local_user',
    summary TEXT NULL,
    message_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id BIGINT NOT NULL,
    role ENUM('user', 'assistant') NOT NULL,
    content TEXT NOT NULL,
    is_summarized BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_chat_messages_session_id_id (session_id, id),
    CONSTRAINT fk_chat_messages_session
        FOREIGN KEY (session_id)
        REFERENCES chat_sessions(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS app_users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(80) NOT NULL UNIQUE,
    display_name VARCHAR(120) NOT NULL,
    role ENUM('admin', 'admin_pro', 'customer', 'customer_pro') NOT NULL DEFAULT 'customer',
    password_salt VARCHAR(64) NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

ALTER TABLE app_users
    MODIFY COLUMN role ENUM('admin', 'admin_pro', 'customer', 'customer_pro') NOT NULL DEFAULT 'customer';

CREATE TABLE IF NOT EXISTS sales_drafts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(128) NOT NULL,
    size_class VARCHAR(32) NOT NULL DEFAULT '대',
    grade VARCHAR(32) NOT NULL,
    quantity_kg INT NOT NULL,
    estimated_unit_weight_kg DECIMAL(6, 3) NOT NULL DEFAULT 0.320,
    price_per_kg INT NOT NULL,
    package_unit VARCHAR(64) NOT NULL,
    sales_channel VARCHAR(64) NOT NULL,
    description TEXT NOT NULL,
    status ENUM('draft', 'approved', 'registered', 'cancelled') NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sales_listings (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    draft_id BIGINT NOT NULL,
    product_name VARCHAR(128) NOT NULL,
    size_class VARCHAR(32) NOT NULL DEFAULT '대',
    grade VARCHAR(32) NOT NULL,
    quantity_kg INT NOT NULL,
    original_quantity_kg INT NOT NULL,
    estimated_unit_weight_kg DECIMAL(6, 3) NOT NULL DEFAULT 0.320,
    price_per_kg INT NOT NULL,
    package_unit VARCHAR(64) NOT NULL,
    sales_channel VARCHAR(64) NOT NULL,
    description TEXT NOT NULL,
    status ENUM('active', 'sold_out', 'closed') NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sales_listings_draft
        FOREIGN KEY (draft_id)
        REFERENCES sales_drafts(id)
);

ALTER TABLE sales_listings
    ADD COLUMN IF NOT EXISTS original_quantity_kg INT NULL AFTER quantity_kg;

ALTER TABLE sales_drafts
    ADD COLUMN IF NOT EXISTS size_class VARCHAR(32) NOT NULL DEFAULT '대' AFTER product_name,
    ADD COLUMN IF NOT EXISTS estimated_unit_weight_kg DECIMAL(6, 3) NOT NULL DEFAULT 0.320 AFTER quantity_kg;

ALTER TABLE sales_listings
    ADD COLUMN IF NOT EXISTS size_class VARCHAR(32) NOT NULL DEFAULT '대' AFTER product_name,
    ADD COLUMN IF NOT EXISTS estimated_unit_weight_kg DECIMAL(6, 3) NOT NULL DEFAULT 0.320 AFTER original_quantity_kg;

CREATE TABLE IF NOT EXISTS sales_orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    listing_id BIGINT NOT NULL,
    customer_user_id BIGINT NULL,
    customer_name VARCHAR(80) NOT NULL,
    quantity_kg INT NOT NULL,
    total_amount INT NOT NULL,
    status ENUM('ordered', 'confirmed', 'cancelled') NOT NULL DEFAULT 'ordered',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sales_orders_listing
        FOREIGN KEY (listing_id)
        REFERENCES sales_listings(id)
);

ALTER TABLE sales_orders
    ADD COLUMN IF NOT EXISTS customer_user_id BIGINT NULL AFTER listing_id;

ALTER TABLE sales_orders
    ADD INDEX IF NOT EXISTS idx_sales_orders_customer_user_id (customer_user_id);

UPDATE sales_listings AS listing
SET original_quantity_kg = quantity_kg + COALESCE((
    SELECT SUM(sales_orders.quantity_kg)
    FROM sales_orders
    WHERE sales_orders.listing_id = listing.id
      AND sales_orders.status <> 'cancelled'
), 0)
WHERE original_quantity_kg IS NULL;

ALTER TABLE sales_listings
    MODIFY original_quantity_kg INT NOT NULL;

CREATE TABLE IF NOT EXISTS notifications (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    event_type VARCHAR(64) NOT NULL,
    title VARCHAR(160) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_settings (
    setting_key VARCHAR(120) PRIMARY KEY,
    setting_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS apple_inventory (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(128) NOT NULL DEFAULT '사과',
    size_class VARCHAR(32) NOT NULL,
    grade VARCHAR(32) NOT NULL,
    available_kg DECIMAL(12, 3) NOT NULL DEFAULT 0,
    reserved_kg DECIMAL(12, 3) NOT NULL DEFAULT 0,
    package_unit VARCHAR(64) NOT NULL,
    sales_channel VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_apple_inventory_product_grade (product_name, size_class, grade)
);

CREATE TABLE IF NOT EXISTS harvest_events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(128) NOT NULL DEFAULT '사과',
    size_class VARCHAR(32) NOT NULL,
    quality_grade VARCHAR(32) NOT NULL,
    estimated_weight_kg DECIMAL(8, 3) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_harvest_events_created_at (created_at),
    INDEX idx_harvest_events_product_grade (product_name, size_class, quality_grade)
);

CREATE TABLE IF NOT EXISTS apple_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(128) NOT NULL DEFAULT '사과',
    size_class VARCHAR(32) NOT NULL,
    quality_grade VARCHAR(32) NOT NULL,
    estimated_weight_kg DECIMAL(8, 3) NOT NULL,
    inventory_status ENUM('available', 'reserved', 'listed', 'sold', 'discarded')
        NOT NULL DEFAULT 'available',
    listing_id BIGINT NULL,
    order_id BIGINT NULL,
    harvested_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_apple_items_product_grade_status (
        product_name, size_class, quality_grade, inventory_status
    ),
    INDEX idx_apple_items_listing_status (listing_id, inventory_status),
    INDEX idx_apple_items_order_id (order_id),
    INDEX idx_apple_items_harvested_at (harvested_at)
);
