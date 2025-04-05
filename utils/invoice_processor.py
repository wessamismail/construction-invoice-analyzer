import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from .ocr_processor import OCRProcessor
import pandas as pd

class InvoiceProcessor:
    def __init__(self):
        """Initialize the invoice processor with OCR capabilities."""
        self.logger = logging.getLogger(__name__)
        self.ocr = OCRProcessor()
        
        # Common Arabic-English patterns for invoice fields
        self.patterns = {
            'invoice_number': r'(?:Invoice\s*(?:#|No|Number)|رقم\s*الفاتورة)\s*[:#]?\s*([A-Za-z0-9-]+)',
            'date': r'(?:Date|التاريخ)\s*[:#]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            'total_amount': r'(?:Total Amount|المبلغ الإجمالي|الإجمالي)\s*[:#]?\s*([\d,]+(?:\.\d{2})?)',
            'tax': r'(?:Tax|VAT|ضريبة القيمة المضافة)\s*[:#]?\s*([\d,]+(?:\.\d{2})?)',
            'vendor': r'(?:Vendor|Company|المورد|الشركة)\s*[:#]?\s*([^\n]+)',
        }

    def process_invoice(self, file_path: str) -> Dict[str, Any]:
        """
        Process an invoice file and extract relevant information.
        
        Args:
            file_path (str): Path to the invoice file (PDF or image)
            
        Returns:
            Dict[str, Any]: Extracted invoice data
        """
        try:
            # Extract text based on file type
            if file_path.lower().endswith('.pdf'):
                text_content = ' '.join(self.ocr.extract_text_from_pdf(file_path))
            else:  # Assume image file
                text_content = self.ocr.extract_text_from_image(file_path)

            # Extract structured data
            structured_data = self.ocr.extract_structured_data(file_path)

            # Combine extracted information
            invoice_data = self._extract_invoice_fields(text_content)
            invoice_data.update(self._process_structured_data(structured_data))

            # Extract table data if present
            invoice_data['line_items'] = self._extract_table_data(text_content)

            return invoice_data

        except Exception as e:
            self.logger.error(f"Error processing invoice {file_path}: {str(e)}")
            return {}

    def _extract_invoice_fields(self, text_content: str) -> Dict[str, Any]:
        """
        Extract key invoice fields using regex patterns.
        
        Args:
            text_content (str): Extracted text from the invoice
            
        Returns:
            Dict[str, Any]: Extracted field values
        """
        invoice_data = {}
        
        for field, pattern in self.patterns.items():
            match = re.search(pattern, text_content, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                
                # Process specific fields
                if field == 'date':
                    try:
                        # Try different date formats
                        for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%Y-%m-%d']:
                            try:
                                value = datetime.strptime(value, fmt).date()
                                break
                            except ValueError:
                                continue
                    except ValueError:
                        self.logger.warning(f"Could not parse date: {value}")
                
                elif field in ['total_amount', 'tax']:
                    try:
                        value = float(value.replace(',', ''))
                    except ValueError:
                        self.logger.warning(f"Could not parse number: {value}")
                
                invoice_data[field] = value
        
        return invoice_data

    def _process_structured_data(self, structured_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Process structured data extracted from the invoice.
        
        Args:
            structured_data (Dict[str, str]): Structured data from OCR
            
        Returns:
            Dict[str, Any]: Processed structured data
        """
        processed_data = {}
        
        # Process key-value pairs
        for key, value in structured_data.items():
            # Skip automatically generated keys
            if key.startswith('text_'):
                continue
                
            # Clean and normalize key
            clean_key = key.lower().strip().replace(' ', '_')
            processed_data[clean_key] = value.strip()
        
        return processed_data

    def _extract_table_data(self, text_content: str) -> List[Dict[str, Any]]:
        """
        Extract table data from invoice text.
        
        Args:
            text_content (str): Extracted text from the invoice
            
        Returns:
            List[Dict[str, Any]]: List of line items
        """
        line_items = []
        
        # Try to identify table structure using common patterns
        table_pattern = r'(?:Item|Description|البند|الوصف)\s+(?:Quantity|الكمية)\s+(?:Price|السعر)\s+(?:Amount|المبلغ)'
        table_match = re.search(table_pattern, text_content, re.IGNORECASE)
        
        if table_match:
            # Get text after table header
            table_content = text_content[table_match.end():].strip()
            
            # Split into lines and process each line
            lines = table_content.split('\n')
            for line in lines:
                # Skip empty lines
                if not line.strip():
                    continue
                    
                # Try to extract item details using spaces or tabs as delimiters
                parts = [part.strip() for part in re.split(r'\s{2,}|\t', line)]
                
                if len(parts) >= 4:
                    try:
                        item = {
                            'description': parts[0],
                            'quantity': float(parts[1].replace(',', '')),
                            'unit_price': float(parts[2].replace(',', '')),
                            'amount': float(parts[3].replace(',', ''))
                        }
                        line_items.append(item)
                    except (ValueError, IndexError):
                        continue
                        
                if len(parts) == 3:
                    try:
                        # Handle cases where quantity is embedded in description
                        item = {
                            'description': parts[0],
                            'unit_price': float(parts[1].replace(',', '')),
                            'amount': float(parts[2].replace(',', ''))
                        }
                        line_items.append(item)
                    except (ValueError, IndexError):
                        continue
        
        return line_items

    def validate_invoice(self, invoice_data: Dict[str, Any]) -> List[str]:
        """
        Validate extracted invoice data.
        
        Args:
            invoice_data (Dict[str, Any]): Extracted invoice data
            
        Returns:
            List[str]: List of validation errors
        """
        errors = []
        
        # Check required fields
        required_fields = ['invoice_number', 'date', 'total_amount']
        for field in required_fields:
            if field not in invoice_data or not invoice_data[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate total amount matches sum of line items
        if 'line_items' in invoice_data and invoice_data['line_items']:
            total_from_items = sum(item['amount'] for item in invoice_data['line_items'])
            if 'total_amount' in invoice_data:
                if abs(total_from_items - invoice_data['total_amount']) > 0.01:
                    errors.append("Total amount does not match sum of line items")
        
        # Validate date
        if 'date' in invoice_data and invoice_data['date']:
            if isinstance(invoice_data['date'], str):
                try:
                    datetime.strptime(invoice_data['date'], '%Y-%m-%d')
                except ValueError:
                    errors.append("Invalid date format")
        
        return errors

    def export_to_excel(self, invoice_data: Dict[str, Any], output_path: str) -> bool:
        """
        Export processed invoice data to Excel.
        
        Args:
            invoice_data (Dict[str, Any]): Processed invoice data
            output_path (str): Path to save the Excel file
            
        Returns:
            bool: True if export successful, False otherwise
        """
        try:
            # Create a DataFrame for invoice header information
            header_data = {k: [v] for k, v in invoice_data.items() if k != 'line_items'}
            header_df = pd.DataFrame(header_data)
            
            # Create a DataFrame for line items if present
            items_df = None
            if 'line_items' in invoice_data and invoice_data['line_items']:
                items_df = pd.DataFrame(invoice_data['line_items'])
            
            # Write to Excel
            with pd.ExcelWriter(output_path) as writer:
                header_df.to_excel(writer, sheet_name='Invoice Info', index=False)
                if items_df is not None:
                    items_df.to_excel(writer, sheet_name='Line Items', index=False)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting invoice data to Excel: {str(e)}")
            return False 