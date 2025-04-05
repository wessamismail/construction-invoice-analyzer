import os
import pytesseract
from PIL import Image
import pdf2image
import cv2
import numpy as np
from typing import List, Dict, Union, Tuple
import logging

class OCRProcessor:
    def __init__(self):
        """Initialize the OCR processor with support for Arabic and English."""
        self.logger = logging.getLogger(__name__)
        # Configure Tesseract to use both Arabic and English
        self.languages = 'ara+eng'
        
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess the image to improve OCR accuracy.
        
        Args:
            image (np.ndarray): Input image
            
        Returns:
            np.ndarray: Preprocessed image
        """
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # Apply thresholding to handle shadows and normalize text
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

            # Noise removal
            denoised = cv2.medianBlur(thresh, 3)

            # Dilation to make text more prominent
            kernel = np.ones((1, 1), np.uint8)
            dilated = cv2.dilate(denoised, kernel, iterations=1)

            return dilated
        except Exception as e:
            self.logger.error(f"Error during image preprocessing: {str(e)}")
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