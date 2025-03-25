import os
import re
import base64
import logging
import io
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
import pdf2image
from flask_cors import CORS
import magic
import cv2
import numpy as np

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def preprocess_image(image):
    """Advanced image preprocessing for better OCR"""
    # Convert to numpy array
    img_array = np.array(image)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # Apply adaptive thresholding
    binary = cv2.adaptiveThreshold(
        gray, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)
    
    # Convert back to PIL Image
    return Image.fromarray(denoised)

def convert_pdf_to_images(pdf_path, output_folder):
    """Convert PDF to images for OCR processing"""
    try:
        # Convert PDF to images with improved parameters
        images = pdf2image.convert_from_path(
            pdf_path, 
            dpi=300,  # Higher DPI for better text recognition
            output_folder=output_folder,
            fmt='jpg',
            first_page=1,
            last_page=3,  # Limit to first 3 pages
            thread_count=2  # Parallel processing
        )
        return images
    except Exception as e:
        logger.error(f"PDF conversion error: {e}")
        return []

def extract_text_from_images(images):
    """Extract text from a list of images with multiple preprocessing techniques"""
    extracted_texts = []
    
    # Tesseract configuration for better accuracy
    custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.() '
    
    for image in images:
        try:
            # Multiple preprocessing techniques
            preprocessing_methods = [
                lambda x: x.convert('L'),  # Grayscale
                preprocess_image,  # Advanced preprocessing
                lambda x: x.point(lambda p: p > 128 and 255)  # Simple thresholding
            ]
            
            for preprocess in preprocessing_methods:
                try:
                    processed_image = preprocess(image)
                    
                    # Extract text with Tesseract
                    text = pytesseract.image_to_string(
                        processed_image, 
                        config=custom_config
                    ).lower().strip()
                    
                    if text and len(text) > 10:  # Ensure meaningful text
                        extracted_texts.append(text)
                        break  # Stop if text is extracted successfully
                except Exception as inner_e:
                    logger.warning(f"Preprocessing method failed: {inner_e}")
        
        except Exception as e:
            logger.error(f"Text extraction error: {e}")
    
    # Combine texts, removing duplicates
    full_text = ' '.join(dict.fromkeys(extracted_texts))
    logger.debug(f"Extracted Text: {full_text}")
    return full_text

# Rest of the code remains the same as in the previous implementation
# (predict_points and upload_certificate functions)

if __name__ == '__main__':
    # Run the Flask app
    app.run(
        host='0.0.0.0', 
        port=int(os.environ.get('PORT', 5000)),
        debug=True
    )
