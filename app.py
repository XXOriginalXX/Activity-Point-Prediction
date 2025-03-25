import os
import re
import base64
import logging
import io
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
from flask_cors import CORS

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

@app.route('/')
def health_check():
    """Basic health check route"""
    return jsonify({
        'status': 'healthy',
        'message': 'Certificate Points Prediction Service is running!'
    }), 200

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image):
    """Apply various preprocessing techniques to improve OCR"""
    # Convert to grayscale
    gray = image.convert('L')
    
    # Apply thresholding to preprocess the image
    threshold = gray.point(lambda x: 0 if x < 128 else 255, '1')
    
    return [
        image,  # Original image
        gray,   # Grayscale image
        threshold  # Binary image
    ]

def extract_text_from_image(file_path):
    """Advanced text extraction with multiple techniques"""
    try:
        # Open the image
        original_image = Image.open(file_path)
        
        # Preprocess images
        image_variants = preprocess_image(original_image)
        
        # Extract text from different image variants
        text_variants = []
        for img in image_variants:
            # Increase tesseract configuration for better accuracy
            text = pytesseract.image_to_string(
                img, 
                config='--psm 6 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.() '
            ).lower()
            text_variants.append(text)
        
        # Combine and clean texts
        full_text = ' '.join(set(filter(bool, text_variants)))
        
        logger.debug(f"Extracted Text: {full_text}")
        return full_text
    except Exception as e:
        logger.error(f"Text extraction error: {e}")
        return ""

def predict_points(text):
    """Predict activity points with comprehensive pattern matching"""
    logger.debug(f"Analyzing text: {text}")

    # Comprehensive point detection patterns
    point_categories = [
        {
            'name': 'NPTEL Certificate',
            'patterns': [
                r'national programme on technology enhanced learning',
                r'nptel',
                r'online certification',
                r'course completed',
                r'completion certificate'
            ],
            'points': 50
        },
        {
            'name': 'Hackathon/Competition',
            'patterns': [
                r'hackathon', 
                r'1st prize', 
                r'winner', 
                r'competition',
                r'national level',
                r'international'
            ],
            'points': 40
        },
        {
            'name': 'Internship',
            'patterns': [
                r'internship', 
                r'industrial training', 
                r'work experience', 
                r'professional training'
            ],
            'points': 30
        },
        {
            'name': 'Professional Development',
            'patterns': [
                r'workshop', 
                r'seminar', 
                r'conference', 
                r'webinar', 
                r'professional development',
                r'skill enhancement'
            ],
            'points': 20
        }
    ]

    # Detailed logging for debugging
    logger.info(f"Full text being analyzed: {text}")

    # Check each category
    for category in point_categories:
        for pattern in category['patterns']:
            if re.search(pattern, text, re.IGNORECASE):
                logger.info(f"Matched category: {category['name']}")
                return {
                    'points': category['points'],
                    'type': category['name']
                }

    # Default points for generic certificates
    logger.warning("No specific category matched. Awarding default points.")
    return {
        'points': 10,
        'type': 'Generic Certificate'
    }

@app.route('/predict-points', methods=['POST'])
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
    filename = data.get('filename', 'certificate.jpg')
    base64_data = data['certificate']

    try:
        # Remove data URL prefix if present
        if base64_data.startswith('data:'):
            base64_data = base64_data.split(',')[1]

        # Decode base64
        image_data = base64.b64decode(base64_data)
        image = Image.open(io.BytesIO(image_data))

        # Save temporary file
        temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        image.save(temp_filepath)

        try:
            # Extract text from image
            extracted_text = extract_text_from_image(temp_filepath)
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
            # Clean up uploaded file
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)

    except Exception as e:
        logger.error(f"Base64 decoding error: {e}")
        return jsonify({
            'error': 'Invalid file format',
            'points': 0
        }), 400

# Error Handlers
@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large errors"""
    return jsonify({
        'error': 'File too large. Maximum file size is 16MB',
        'points': 0
    }), 413

if __name__ == '__main__':
    # Ensure Tesseract is installed and configured
    pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Update this path if needed
