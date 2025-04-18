import os
import re
import base64
import logging
import io
import mimetypes
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
import pdf2image
from flask_cors import CORS
import cv2
import numpy as np

# Fallback for magic if not available
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask application
application = Flask(__name__)
CORS(application)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
application.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
application.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def detect_mime_type(file_data):
    """
    Detect MIME type with fallback methods
    """
    # Try magic if available
    if HAS_MAGIC:
        try:
            return magic.from_buffer(file_data, mime=True)
        except Exception as e:
            logger.warning(f"Magic MIME detection failed: {e}")
    
    # Fallback to mimetypes
    try:
        # Guess mime type from file extension
        guessed_type = mimetypes.guess_type(file_data)[0]
        if guessed_type:
            return guessed_type
    except Exception as e:
        logger.warning(f"Mimetypes detection failed: {e}")
    
    # Last resort fallback
    return 'application/octet-stream'

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
            'type': 'NPTEL',
            'keywords': ['nptel', 'national programme', 'online certification'],
            'points': 50
        },
        {
            'type': 'Hackathon/Competition',
            'keywords': ['hackathon', 'competition', 'challenge', 'winner'],
            'points': 40
        },
        {
            'type': 'Internship',
            'keywords': ['internship', 'intern', 'training'],
            'points': 30
        },
        {
            'type': 'Professional Development',
            'keywords': ['professional', 'development', 'workshop', 'seminar', 'course'],
            'points': 20
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
        'type': 'Other Certificate',
        'points': 10
    }

@application.route('/predict-points', methods=['POST'])
def upload_certificate():
    """Certificate points prediction endpoint"""
    # Check if request is JSON
    if not request.is_json:
        logger.error("Request must be JSON")
        return jsonify({
            'error': 'Invalid request format',
            'points': 0
        }), 400

    # Get request data
    data = request.get_json()
    
    # Validate input
    if not data or 'certificate' not in data:
        logger.error("No file uploaded")
        return jsonify({
            'error': 'No file uploaded',
            'points': 0
        }), 400

    # Extract data
    username = data.get('username', 'Unknown User')
    filename = data.get('filename', 'certificate')
    base64_data = data['certificate']

    try:
        # Remove data URL prefix if present
        if base64_data.startswith('data:'):
            base64_data = base64_data.split(',')[1]

        # Decode base64
        file_data = base64.b64decode(base64_data)
        
        # Detect MIME type
        mime_type = detect_mime_type(file_data)
        logger.info(f"Detected MIME type: {mime_type}")

        # Validate file type
        if mime_type not in [
            'application/pdf', 
            'image/jpeg', 
            'image/png', 
            'image/jpg'
        ]:
            return jsonify({
                'error': f'Unsupported file type: {mime_type}',
                'points': 0
            }), 400

        # Determine file extension
        file_extension = mime_type.split('/')[-1]
        if file_extension == 'jpeg':
            file_extension = 'jpg'

        # Save temporary file
        temp_filepath = os.path.join(
            application.config['UPLOAD_FOLDER'], 
            f"{secure_filename(filename)}.{file_extension}"
        )
        
        with open(temp_filepath, 'wb') as f:
            f.write(file_data)

        try:
            # Process different file types
            if file_extension == 'pdf':
                # Convert PDF to images
                images = convert_pdf_to_images(temp_filepath, application.config['UPLOAD_FOLDER'])
                if not images:
                    raise ValueError("Could not convert PDF to images")
                
                # Extract text from PDF images
                extracted_text = extract_text_from_images(images)
            else:
                # For image files, use PIL and Tesseract directly
                image = Image.open(temp_filepath)
                extracted_text = extract_text_from_images([image])

            logger.info(f"Full Extracted Text: {extracted_text}")

            # Predict points
            point_result = predict_points(extracted_text)
            logger.info(f"Points awarded: {point_result['points']}")

            return jsonify({
                'username': username,
                'points': point_result['points'],
                'certificateType': point_result['type']
            }), 200

        except Exception as e:
            logger.error(f"Processing error: {e}")
            return jsonify({
                'error': f'Processing error: {str(e)}',
                'points': 0
            }), 500
        finally:
            # Clean up uploaded file and converted images
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)
            
            # Remove any generated PDF images
            for f in os.listdir(application.config['UPLOAD_FOLDER']):
                if f.endswith('.jpg'):
                    os.remove(os.path.join(application.config['UPLOAD_FOLDER'], f))

    except Exception as e:
        logger.error(f"Base64 decoding error: {e}")
        return jsonify({
            'error': 'Invalid file format',
            'points': 0
        }), 400

if __name__ == '__main__':
    # Run the Flask app
    application.run(
        host='0.0.0.0', 
        port=int(os.environ.get('PORT', 5000)),
        debug=True
    )
