import sqlite3
import pandas as pd
from datetime import datetime
import json
from typing import Dict, Any, List, Tuple
import os
import shutil
import zipfile
import glob
import hashlib

class Database:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'invoice_analyzer.db')
        self.backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'backups')
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        self.init_database()

    def init_database(self):
        """Initialize database tables with versioning support."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create version tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS db_version (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            ''')
            
            # Create data validation table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_validation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    record_id INTEGER NOT NULL,
                    validation_type TEXT NOT NULL,
                    validation_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create data statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stat_date DATE NOT NULL,
                    total_invoices INTEGER,
                    total_amount REAL,
                    avg_variance REAL,
                    unique_vendors INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create initial pricing table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS initial_pricing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_description TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    base_price REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create invoices table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_number TEXT NOT NULL,
                    vendor_name TEXT,
                    invoice_date DATE,
                    total_amount REAL,
                    file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create invoice items table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invoice_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER,
                    item_description TEXT NOT NULL,
                    quantity REAL,
                    unit TEXT,
                    unit_price REAL,
                    total_price REAL,
                    FOREIGN KEY (invoice_id) REFERENCES invoices (id)
                )
            ''')
            
            # Create variance analysis table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS variance_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER,
                    item_description TEXT NOT NULL,
                    base_price REAL,
                    actual_price REAL,
                    variance_amount REAL,
                    variance_percentage REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (invoice_id) REFERENCES invoices (id)
                )
            ''')
            
            # Set initial version if not exists
            cursor.execute('SELECT COUNT(*) FROM db_version')
            if cursor.fetchone()[0] == 0:
                cursor.execute('INSERT INTO db_version (version, description) VALUES (1, "Initial schema")')
            
            conn.commit()

    def validate_data(self, table: str, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate data before insertion."""
        errors = []
        
        if table == 'invoices':
            if not data.get('invoice_number'):
                errors.append("Invoice number is required")
            if not data.get('vendor_name'):
                errors.append("Vendor name is required")
            if not data.get('invoice_date'):
                errors.append("Invoice date is required")
            if not data.get('total_amount'):
                errors.append("Total amount is required")
        
        elif table == 'invoice_items':
            if not data.get('item_description'):
                errors.append("Item description is required")
            if not data.get('quantity'):
                errors.append("Quantity is required")
            if not data.get('unit_price'):
                errors.append("Unit price is required")
        
        return len(errors) == 0, errors

    def save_initial_pricing(self, pricing_data: pd.DataFrame) -> bool:
        """Save initial pricing data to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Clear existing pricing data
                conn.execute('DELETE FROM initial_pricing')
                
                # Insert new pricing data
                pricing_data.to_sql('initial_pricing', conn, if_exists='append', index=False)
                return True
        except Exception as e:
            print(f"Error saving initial pricing: {e}")
            return False

    def get_initial_pricing(self) -> pd.DataFrame:
        """Retrieve initial pricing data."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql_query('SELECT * FROM initial_pricing', conn)
        except Exception as e:
            print(f"Error retrieving initial pricing: {e}")
            return pd.DataFrame()

    def save_invoice(self, invoice_data: Dict[str, Any], file_path: str) -> int:
        """Save invoice with validation and error tracking."""
        try:
            # Validate invoice data
            is_valid, errors = self.validate_data('invoices', invoice_data)
            if not is_valid:
                raise ValueError(f"Invalid invoice data: {', '.join(errors)}")

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Calculate checksum for duplicate detection
                checksum = hashlib.md5(
                    f"{invoice_data.get('invoice_number')}_{invoice_data.get('vendor_name')}_{invoice_data.get('total_amount')}".encode()
                ).hexdigest()
                
                # Check for duplicates
                cursor.execute(
                    'SELECT id FROM invoices WHERE invoice_number = ? AND vendor_name = ?',
                    (invoice_data.get('invoice_number'), invoice_data.get('vendor_name'))
                )
                if cursor.fetchone():
                    raise ValueError("Duplicate invoice detected")
                
                # Insert invoice with additional metadata
                cursor.execute('''
                    INSERT INTO invoices (
                        invoice_number, vendor_name, invoice_date, total_amount,
                        file_path, checksum, processing_status, error_message
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    invoice_data.get('invoice_number'),
                    invoice_data.get('vendor_name'),
                    invoice_data.get('date'),
                    invoice_data.get('total_amount'),
                    file_path,
                    checksum,
                    'processed',
                    None
                ))
                
                invoice_id = cursor.lastrowid
                
                # Validate and insert invoice items
                for item in invoice_data.get('items', []):
                    is_valid, errors = self.validate_data('invoice_items', item)
                    if not is_valid:
                        raise ValueError(f"Invalid item data: {', '.join(errors)}")
                    
                    cursor.execute('''
                        INSERT INTO invoice_items (
                            invoice_id, item_description, quantity, unit,
                            unit_price, total_price, status
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        invoice_id,
                        item.get('description'),
                        item.get('quantity'),
                        item.get('unit'),
                        item.get('unit_price'),
                        item.get('total_price'),
                        'active'
                    ))
                
                # Update statistics
                self.update_statistics()
                
                conn.commit()
                return invoice_id
        except Exception as e:
            print(f"Error saving invoice: {e}")
            # Log error for tracking
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO data_validation (
                        table_name, record_id, validation_type, validation_message
                    )
                    VALUES (?, ?, ?, ?)
                ''', ('invoices', 0, 'error', str(e)))
                conn.commit()
            return 0

    def save_variance_analysis(self, invoice_id: int, analysis_data: Dict[str, Any]) -> bool:
        """Save variance analysis results."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for item in analysis_data.get('items_analysis', []):
                    cursor.execute('''
                        INSERT INTO variance_analysis (
                            invoice_id, item_description, base_price,
                            actual_price, variance_amount, variance_percentage
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        invoice_id,
                        item.get('description'),
                        item.get('base_price'),
                        item.get('actual_price'),
                        item.get('variance_amount'),
                        item.get('variance_percentage')
                    ))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving variance analysis: {e}")
            return False

    def get_invoice_history(self) -> List[Dict[str, Any]]:
        """Retrieve invoice history with variance analysis."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        i.invoice_number,
                        i.vendor_name,
                        i.invoice_date,
                        i.total_amount,
                        GROUP_CONCAT(va.item_description || ':' || va.variance_percentage, ';') as variances
                    FROM invoices i
                    LEFT JOIN variance_analysis va ON i.id = va.invoice_id
                    GROUP BY i.id
                    ORDER BY i.invoice_date DESC
                ''')
                
                results = []
                for row in cursor.fetchall():
                    invoice = {
                        'invoice_number': row[0],
                        'vendor_name': row[1],
                        'date': row[2],
                        'total_amount': row[3],
                        'variances': {}
                    }
                    
                    if row[4]:  # If there are variances
                        for variance in row[4].split(';'):
                            item, value = variance.split(':')
                            invoice['variances'][item] = float(value)
                    
                    results.append(invoice)
                
                return results
        except Exception as e:
            print(f"Error retrieving invoice history: {e}")
            return []

    def get_trend_data(self) -> pd.DataFrame:
        """Retrieve trend data for analysis."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql_query('''
                    SELECT 
                        i.invoice_date,
                        va.item_description,
                        va.variance_percentage
                    FROM variance_analysis va
                    JOIN invoices i ON va.invoice_id = i.id
                    ORDER BY i.invoice_date
                ''', conn)
        except Exception as e:
            print(f"Error retrieving trend data: {e}")
            return pd.DataFrame()

    def update_statistics(self):
        """Update data statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Calculate daily statistics
                cursor.execute('''
                    INSERT INTO data_statistics (
                        stat_date, total_invoices, total_amount,
                        avg_variance, unique_vendors
                    )
                    SELECT 
                        DATE('now'),
                        COUNT(DISTINCT i.id),
                        SUM(i.total_amount),
                        AVG(va.variance_percentage),
                        COUNT(DISTINCT i.vendor_name)
                    FROM invoices i
                    LEFT JOIN variance_analysis va ON i.id = va.invoice_id
                ''')
                
                conn.commit()
        except Exception as e:
            print(f"Error updating statistics: {e}")

    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get data statistics for the specified period."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        COUNT(DISTINCT i.id) as total_invoices,
                        SUM(i.total_amount) as total_amount,
                        COUNT(DISTINCT i.vendor_name) as unique_vendors,
                        AVG(va.variance_percentage) as avg_variance,
                        COUNT(DISTINCT CASE WHEN va.variance_percentage > 10 THEN i.id END) as high_variance_invoices
                    FROM invoices i
                    LEFT JOIN variance_analysis va ON i.id = va.invoice_id
                    WHERE i.invoice_date >= DATE('now', ?)
                ''', (f'-{days} days',))
                
                row = cursor.fetchone()
                return {
                    'total_invoices': row[0] or 0,
                    'total_amount': row[1] or 0,
                    'unique_vendors': row[2] or 0,
                    'avg_variance': row[3] or 0,
                    'high_variance_invoices': row[4] or 0
                }
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}

    def search_invoices(self, 
                       query: str = None,
                       start_date: datetime = None,
                       end_date: datetime = None,
                       vendor: str = None,
                       min_amount: float = None,
                       max_amount: float = None,
                       variance_threshold: float = None,
                       sort_by: str = 'date',
                       sort_order: str = 'desc',
                       limit: int = 100) -> List[Dict[str, Any]]:
        """Enhanced search with additional filters and sorting."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build query with additional filters
                sql = '''
                    SELECT 
                        i.invoice_number,
                        i.vendor_name,
                        i.invoice_date,
                        i.total_amount,
                        i.file_path,
                        i.processing_status,
                        GROUP_CONCAT(DISTINCT ii.item_description) as items,
                        GROUP_CONCAT(va.variance_percentage) as variances,
                        AVG(va.variance_percentage) as avg_variance
                    FROM invoices i
                    LEFT JOIN invoice_items ii ON i.id = ii.invoice_id
                    LEFT JOIN variance_analysis va ON i.id = va.invoice_id
                    WHERE 1=1
                '''
                params = []
                
                if query:
                    sql += ''' AND (
                        i.invoice_number LIKE ? OR
                        i.vendor_name LIKE ? OR
                        ii.item_description LIKE ?
                    )'''
                    params.extend([f"%{query}%"] * 3)
                
                if start_date:
                    sql += ' AND i.invoice_date >= ?'
                    params.append(start_date.strftime('%Y-%m-%d'))
                
                if end_date:
                    sql += ' AND i.invoice_date <= ?'
                    params.append(end_date.strftime('%Y-%m-%d'))
                
                if vendor:
                    sql += ' AND i.vendor_name LIKE ?'
                    params.append(f"%{vendor}%")
                
                if min_amount is not None:
                    sql += ' AND i.total_amount >= ?'
                    params.append(min_amount)
                
                if max_amount is not None:
                    sql += ' AND i.total_amount <= ?'
                    params.append(max_amount)
                
                if variance_threshold is not None:
                    sql += ' HAVING avg_variance >= ?'
                    params.append(variance_threshold)
                
                # Add sorting
                sort_column = {
                    'date': 'i.invoice_date',
                    'amount': 'i.total_amount',
                    'variance': 'avg_variance'
                }.get(sort_by, 'i.invoice_date')
                
                sql += f' GROUP BY i.id ORDER BY {sort_column} {sort_order}'
                
                if limit:
                    sql += ' LIMIT ?'
                    params.append(limit)
                
                cursor.execute(sql, params)
                
                results = []
                for row in cursor.fetchall():
                    invoice = {
                        'invoice_number': row[0],
                        'vendor_name': row[1],
                        'date': row[2],
                        'total_amount': row[3],
                        'file_path': row[4],
                        'status': row[5],
                        'items': row[6].split(',') if row[6] else [],
                        'variances': [float(v) for v in row[7].split(',')] if row[7] else [],
                        'avg_variance': row[8]
                    }
                    results.append(invoice)
                
                return results
        except Exception as e:
            print(f"Error searching invoices: {e}")
            return []

    def backup_database(self) -> str:
        """Create a versioned backup with metadata."""
        try:
            # Create backup directory with timestamp and version
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            version = self.get_current_version()
            backup_path = os.path.join(self.backup_dir, f"backup_v{version}_{timestamp}")
            os.makedirs(backup_path, exist_ok=True)

            # Create backup metadata
            metadata = {
                'version': version,
                'timestamp': timestamp,
                'stats': self.get_statistics(),
                'file_count': {
                    'invoices': len(glob.glob(os.path.join(self.data_dir, 'invoices', '*'))),
                    'pricing': len(glob.glob(os.path.join(self.data_dir, 'pricing', '*')))
                }
            }

            # Save metadata
            with open(os.path.join(backup_path, 'metadata.json'), 'w') as f:
                json.dump(metadata, f, indent=2)

            # Backup database and files
            shutil.copy2(self.db_path, os.path.join(backup_path, "invoice_analyzer.db"))
            for directory in ['invoices', 'pricing']:
                src_dir = os.path.join(self.data_dir, directory)
                if os.path.exists(src_dir):
                    dst_dir = os.path.join(backup_path, directory)
                    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)

            # Create zip file with metadata
            zip_path = f"{backup_path}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(backup_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, backup_path)
                        zipf.write(file_path, arcname)

            # Clean up temporary backup directory
            shutil.rmtree(backup_path)

            return zip_path
        except Exception as e:
            print(f"Error creating backup: {e}")
            return ""

    def get_current_version(self) -> int:
        """Get current database version."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT MAX(version) FROM db_version')
                return cursor.fetchone()[0] or 1
        except Exception as e:
            print(f"Error getting version: {e}")
            return 1

    def restore_backup(self, backup_zip_path: str) -> bool:
        """Restore database and files from a backup."""
        try:
            # Create temporary directory for restoration
            temp_dir = os.path.join(self.backup_dir, "temp_restore")
            os.makedirs(temp_dir, exist_ok=True)

            # Extract backup
            with zipfile.ZipFile(backup_zip_path, 'r') as zipf:
                zipf.extractall(temp_dir)

            # Stop database connections
            self.__del__()

            # Restore database
            shutil.copy2(
                os.path.join(temp_dir, "invoice_analyzer.db"),
                self.db_path
            )

            # Restore uploaded files
            for directory in ['invoices', 'pricing']:
                src_dir = os.path.join(temp_dir, directory)
                if os.path.exists(src_dir):
                    dst_dir = os.path.join(self.data_dir, directory)
                    if os.path.exists(dst_dir):
                        shutil.rmtree(dst_dir)
                    shutil.copytree(src_dir, dst_dir)

            # Clean up
            shutil.rmtree(temp_dir)

            return True
        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False

    def export_data(self, export_dir: str) -> bool:
        """Export database data to CSV files."""
        try:
            os.makedirs(export_dir, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                # Export tables to CSV
                tables = [
                    'initial_pricing',
                    'invoices',
                    'invoice_items',
                    'variance_analysis'
                ]
                
                for table in tables:
                    df = pd.read_sql_query(f'SELECT * FROM {table}', conn)
                    df.to_csv(
                        os.path.join(export_dir, f"{table}.csv"),
                        index=False
                    )
            
            return True
        except Exception as e:
            print(f"Error exporting data: {e}")
            return False

    def import_data(self, import_dir: str) -> bool:
        """Import data from CSV files into database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Import tables from CSV
                tables = [
                    'initial_pricing',
                    'invoices',
                    'invoice_items',
                    'variance_analysis'
                ]
                
                for table in tables:
                    csv_path = os.path.join(import_dir, f"{table}.csv")
                    if os.path.exists(csv_path):
                        df = pd.read_csv(csv_path)
                        df.to_sql(table, conn, if_exists='replace', index=False)
            
            return True
        except Exception as e:
            print(f"Error importing data: {e}")
            return False

    def cleanup_old_files(self, days_old: int = 30) -> bool:
        """Clean up old files and backups."""
        try:
            cutoff_date = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
            
            # Clean up old backups
            for backup in glob.glob(os.path.join(self.backup_dir, "backup_*.zip")):
                if os.path.getctime(backup) < cutoff_date:
                    os.remove(backup)
            
            # Clean up old files
            for directory in ['invoices', 'pricing']:
                dir_path = os.path.join(self.data_dir, directory)
                if os.path.exists(dir_path):
                    for file in os.listdir(dir_path):
                        file_path = os.path.join(dir_path, file)
                        if os.path.getctime(file_path) < cutoff_date:
                            os.remove(file_path)
            
            return True
        except Exception as e:
            print(f"Error cleaning up files: {e}")
            return False

    def __del__(self):
        """Cleanup method to ensure database connections are closed."""
        try:
            sqlite3.connect(self.db_path).close()
        except:
            pass 