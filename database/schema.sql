-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    start_date DATE,
    end_date DATE,
    budget DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Initial pricing table
CREATE TABLE IF NOT EXISTS initial_pricing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    item_code TEXT,
    description TEXT,
    unit TEXT,
    unit_price DECIMAL(15,2),
    estimated_quantity DECIMAL(15,2),
    total_amount DECIMAL(15,2),
    category TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    invoice_number TEXT,
    vendor_name TEXT,
    invoice_date DATE,
    total_amount DECIMAL(15,2),
    status TEXT,
    file_path TEXT,
    file_type TEXT,
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Invoice items table
CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER,
    item_code TEXT,
    description TEXT,
    unit TEXT,
    quantity DECIMAL(15,2),
    unit_price DECIMAL(15,2),
    total_amount DECIMAL(15,2),
    category TEXT,
    initial_pricing_id INTEGER,
    price_difference DECIMAL(15,2),
    quantity_difference DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (initial_pricing_id) REFERENCES initial_pricing(id)
);

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    parent_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES categories(id)
);

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    invoice_id INTEGER,
    alert_type TEXT,
    message TEXT,
    severity TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

-- Weekly reports table
CREATE TABLE IF NOT EXISTS weekly_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    week_start_date DATE,
    week_end_date DATE,
    total_invoices INTEGER,
    total_amount DECIMAL(15,2),
    variance_amount DECIMAL(15,2),
    report_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
); 