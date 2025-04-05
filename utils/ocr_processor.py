import os
from typing import List, Dict, Any
import pdfplumber
from PIL import Image
import io
import easyocr
import numpy as np
import cv2

class OCRProcessor:
    def __init__(self):
        """Initialize the OCR processor with support for Arabic and English."""
        # Initialize EasyOCR reader with Arabic and English support
        self.reader = easyocr.Reader(['ar', 'en'])
        
    def process_pdf(self, file_path: str) -> str:
        """Extract text from PDF file using EasyOCR."""
        text_content = []
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # Convert PDF page to image
                image = page.to_image()
                image_bytes = io.BytesIO()
                image.save(image_bytes, format='PNG')
                image_bytes = image_bytes.getvalue()
                
                # Convert to numpy array for OpenCV
                nparr = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                # Process with EasyOCR
                results = self.reader.readtext(img)
                page_text = ' '.join([text for _, text, _ in results])
                text_content.append(page_text)
        
        return '\n'.join(text_content)

    def process_image(self, file_path: str) -> str:
        """Extract text from image file using EasyOCR."""
        # Read image with OpenCV
        img = cv2.imread(file_path)
        if img is None:
            raise Exception(f"Could not read image file: {file_path}")
        
        # Process with EasyOCR
        results = self.reader.readtext(img)
        return ' '.join([text for _, text, _ in results])

    def extract_text(self, file_path: str) -> str:
        """Extract text from file (PDF or image) using appropriate method."""
        try:
            if file_path.lower().endswith('.pdf'):
                return self.process_pdf(file_path)
            else:
                return self.process_image(file_path)
        except Exception as e:
            raise Exception(f"Error extracting text: {str(e)}")

    def detect_language(self, text: str) -> str:
        """Detect the language of the extracted text."""
        try:
            # Simple language detection based on character sets
            arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
            english_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
            
            if arabic_chars > english_chars:
                return "ar"
            return "en"
        except Exception as e:
            print(f"Error detecting language: {str(e)}")
            return "en"  # Default to English if detection fails

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image to improve OCR accuracy."""
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )

            # Denoise
            denoised = cv2.fastNlMeansDenoising(thresh)

            return denoised
        except Exception as e:
            print(f"Error in image preprocessing: {str(e)}")
            return image

    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from an image file.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            str: Extracted text
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image at path: {image_path}")

            # Preprocess image
            processed_image = self.preprocess_image(image)

            # Extract text using Tesseract
            text = pytesseract.image_to_string(
                processed_image,
                lang=self.languages,
                config='--psm 1 --oem 3'  # Page segmentation mode: Automatic page segmentation with OSD
            )

            return text.strip()
        except Exception as e:
            self.logger.error(f"Error extracting text from image {image_path}: {str(e)}")
            return ""

    def extract_text_from_pdf(self, pdf_path: str) -> List[str]:
        """
        Extract text from a PDF file by converting each page to an image.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            List[str]: List of extracted text from each page
        """
        try:
            # Convert PDF to images
            images = pdf2image.convert_from_path(pdf_path)
            extracted_texts = []

            for i, image in enumerate(images):
                # Convert PIL Image to OpenCV format
                opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # Preprocess image
                processed_image = self.preprocess_image(opencv_image)
                
                # Extract text
                text = pytesseract.image_to_string(
                    processed_image,
                    lang=self.languages,
                    config='--psm 1 --oem 3'
                )
                
                extracted_texts.append(text.strip())

            return extracted_texts
        except Exception as e:
            self.logger.error(f"Error extracting text from PDF {pdf_path}: {str(e)}")
            return []

    def extract_structured_data(self, image_path: str) -> Dict[str, str]:
        """
        Extract structured data (tables, key-value pairs) from an image.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            Dict[str, str]: Dictionary containing extracted structured data
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image at path: {image_path}")

            # Preprocess image
            processed_image = self.preprocess_image(image)

            # Extract structured data using Tesseract
            data = pytesseract.image_to_data(
                processed_image,
                lang=self.languages,
                config='--psm 1 --oem 3',
                output_type=pytesseract.Output.DICT
            )

            # Process the structured data
            structured_data = {}
            n_boxes = len(data['text'])
            
            # Combine text elements with their confidence scores
            for i in range(n_boxes):
                if int(data['conf'][i]) > 60:  # Filter low-confidence results
                    text = data['text'][i].strip()
                    if text:
                        # Try to identify key-value pairs
                        if ':' in text:
                            key, value = text.split(':', 1)
                            structured_data[key.strip()] = value.strip()
                        else:
                            # Store other high-confidence text
                            structured_data[f'text_{i}'] = text

            return structured_data
        except Exception as e:
            self.logger.error(f"Error extracting structured data from {image_path}: {str(e)}")
            return {}

    def detect_text_regions(self, image_path: str) -> List[Tuple[int, int, int, int]]:
        """
        Detect regions containing text in an image.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            List[Tuple[int, int, int, int]]: List of bounding boxes (x, y, w, h)
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not read image at path: {image_path}")

            # Preprocess image
            processed_image = self.preprocess_image(image)

            # Get bounding boxes for text regions
            boxes = pytesseract.image_to_boxes(
                processed_image,
                lang=self.languages,
                config='--psm 1 --oem 3'
            )

            # Convert boxes to list of tuples
            text_regions = []
            for box in boxes.splitlines():
                b = box.split()
                if len(b) >= 4:
                    x, y, w, h = int(b[1]), int(b[2]), int(b[3]), int(b[4])
                    text_regions.append((x, y, w, h))

            return text_regions
        except Exception as e:
            self.logger.error(f"Error detecting text regions in {image_path}: {str(e)}")
            return [] 