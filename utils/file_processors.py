import pandas as pd
import pdfplumber
import pytesseract
from PIL import Image
import openai
import os
from dotenv import load_dotenv
from pathlib import Path
import json

# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

# Xero configuration
XERO_CLIENT_ID = os.getenv('XERO_CLIENT_ID')
XERO_CLIENT_SECRET = os.getenv('XERO_CLIENT_SECRET')
XERO_REDIRECT_URI = os.getenv('XERO_REDIRECT_URI')

class FileProcessor:
    @staticmethod
    def process_excel(file_path):
        """Process Excel files and extract invoice data."""
        try:
            df = pd.read_excel(file_path)
            # Implement smart column detection logic here
            return df.to_dict('records')
        except Exception as e:
            print(f"Error processing Excel file: {e}")
            return None

    @staticmethod
    def process_pdf(file_path):
        """Process PDF files and extract invoice data using pdfplumber."""
        try:
            extracted_text = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    extracted_text.append(text)
            
            # Use GPT to structure the extracted text
            structured_data = FileProcessor._structure_with_gpt('\n'.join(extracted_text))
            return structured_data
        except Exception as e:
            print(f"Error processing PDF file: {e}")
            return None

    @staticmethod
    def process_image(file_path):
        """Process image files and extract invoice data using OCR."""
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image, lang='ara+eng')
            
            # Use GPT to structure the extracted text
            structured_data = FileProcessor._structure_with_gpt(text)
            return structured_data
        except Exception as e:
            print(f"Error processing image file: {e}")
            return None

    @staticmethod
    def _structure_with_gpt(text):
        """Use GPT to structure extracted text into invoice data."""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": """
                    Extract and structure the following invoice information into JSON format:
                    - Invoice number
                    - Date
                    - Vendor name
                    - Line items (including: item code, description, unit, quantity, unit price, total)
                    - Total amount
                    """},
                    {"role": "user", "content": text}
                ]
            )
            
            # Parse the structured data from GPT's response
            structured_data = json.loads(response.choices[0].message.content)
            return structured_data
        except Exception as e:
            print(f"Error structuring data with GPT: {e}")
            return None

    @staticmethod
    def detect_file_type(file_path):
        """Detect the type of file based on extension."""
        extension = Path(file_path).suffix.lower()
        if extension in ['.xlsx', '.xls']:
            return 'excel'
        elif extension == '.pdf':
            return 'pdf'
        elif extension in ['.jpg', '.jpeg', '.png', '.tiff']:
            return 'image'
        else:
            raise ValueError(f"Unsupported file type: {extension}")

    @staticmethod
    def process_file(file_path):
        """Process any supported file type and return structured data."""
        file_type = FileProcessor.detect_file_type(file_path)
        
        if file_type == 'excel':
            return FileProcessor.process_excel(file_path)
        elif file_type == 'pdf':
            return FileProcessor.process_pdf(file_path)
        elif file_type == 'image':
            return FileProcessor.process_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}") 
        