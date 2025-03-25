import os
import pdf2image
import pytesseract
from PIL import Image
import cv2
import numpy as np

def convert_pdf_to_images(pdf_path, output_folder):
    """
    Convert PDF pages to images
    
    Args:
        pdf_path (str): Path to the PDF file
        output_folder (str): Folder to save converted images
    
    Returns:
        list: List of PIL Image objects
    """
    try:
        # Convert PDF to list of images
        images = pdf2image.convert_from_path(
            pdf_path, 
            dpi=300,  # Higher DPI for better quality
            output_folder=output_folder,
            fmt='jpg',
            output_file=os.path.splitext(os.path.basename(pdf_path))[0]
        )
        return images
    except Exception as e:
        logger.error(f"PDF conversion error: {e}")
        return []

def extract_text_from_images(images):
    """
    Extract text from a list of images using Tesseract OCR
    
    Args:
        images (list): List of PIL Image objects
    
    Returns:
        str: Extracted text from all images
    """
    extracted_texts = []
    
    for image in images:
        # Preprocess image for better OCR
        processed_image = preprocess_image(image)
        
        # Extract text using Tesseract
        text = pytesseract.image_to_string(
            processed_image, 
            config='--psm 6'  # Assume a single uniform block of text
        )
        
        extracted_texts.append(text.strip())
    
    # Combine texts from all pages
    return ' '.join(extracted_texts)

def predict_points(extracted_text):
    """
    Predict points based on certificate text
    
    Args:
        extracted_text (str): Text extracted from certificate
    
    Returns:
        dict: Points and certificate type
    """
    # Lowercase for case-insensitive matching
    text = extracted_text.lower()
    
    # Define point rules
    certificate_rules = [
        {
            'type': 'Advanced',
            'keywords': ['advanced', 'professional', 'expert'],
            'points': 50
        },
        {
            'type': 'Intermediate',
            'keywords': ['intermediate', 'mid-level', 'standard'],
            'points': 30
        },
        {
            'type': 'Beginner',
            'keywords': ['beginner', 'entry', 'basic', 'starter'],
            'points': 10
        }
    ]
    
    # Check for certificate type
    for rule in certificate_rules:
        if any(keyword in text for keyword in rule['keywords']):
            return {
                'type': rule['type'],
                'points': rule['points']
            }
    
    # Default if no match
    return {
        'type': 'Unrecognized',
        'points': 0
    }
