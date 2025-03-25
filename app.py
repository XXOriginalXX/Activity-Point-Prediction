import os
import re
import logging
import numpy as np
from flask import Flask, request, jsonify
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

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_image(file_path):
    """Extract text from uploaded image using OCR with multiple techniques"""
    try:
        # Open image and preprocess
        image = Image.open(file_path)
        
        # Try multiple preprocessing techniques
        preprocessing_techniques = [
            lambda img: img.convert('L'),  # Grayscale
            lambda img: img.convert('L').point(lambda x: 0 if x < 128 else 255, '1'),  # Binary
        ]

        extracted_texts = []
        for preprocess in preprocessing_techniques:
            processed_image = preprocess(image)
            text = pytesseract.image_to_string(processed_image, lang='eng')
            extracted_texts.append(text.lower())
            logger.debug(f"Extracted text (preprocessing technique): {text}")

        # Combine and deduplicate texts
        full_text = ' '.join(set(extracted_texts))
        
        logger.debug(f"Final extracted text: {full_text}")
        return full_text
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return ""

def predict_points(text):
    """Predict activity points with comprehensive pattern matching"""
    logger.debug(f"Analyzing text for points: {text}")

    # Comprehensive NPTEL detection patterns
    nptel_patterns = [
        r'national programme on technology enhanced learning',
        r'nptel',
        r'online certification',
        r'course completed',
        r'certificate of completion'
    ]

    # Check for NPTEL patterns
    for pattern in nptel_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.info("NPTEL Certificate Detected!")
            return 50

    # Specific patterns for different point categories
    point_categories = [
        # Hackathon achievements
        {
            'patterns': [r'hackathon', r'1st prize', r'winner'],
            'points': 25
        },
        # Internships
        {
            'patterns': [r'internship', r'industrial training'],
            'points': 25
        },
        # Professional development
        {
            'patterns': [r'workshop', r'seminar', r'conference', r'webinar'],
            'points': 20
        }
    ]

    # Check other point categories
    for category in point_categories:
        for pattern in category['patterns']:
            if re.search(pattern, text, re.IGNORECASE):
                logger.info(f"Matched category: {pattern}")
                return category['points']

    # Default points with logging
    logger.warning("No specific category matched. Awarding default points.")
    return 10

def validate_certificate(text):
    """Advanced certificate validation"""
    # Minimum text length check
    if len(text) < 50:
        logger.warning(f"Certificate text too short: {len(text)} characters")
        return False

    # Check for certificate indicators
    certificate_indicators = [
        'certificate', 
        'completion', 
        'awarded', 
        'verified', 
        'recognized'
    ]
    
    # Count meaningful indicators
    indicator_count = sum(1 for indicator in certificate_indicators if indicator in text.lower())
    
    is_valid = indicator_count > 1
    logger.debug(f"Certificate validation - Indicators found: {indicator_count}, Valid: {is_valid}")
    return is_valid

@app.route('/predict-points', methods=['POST'])
def upload_certificate():
    # File upload and processing logic
    if 'certificate' not in request.files:
        logger.error("No file uploaded")
        return jsonify({
            'error': 'No file uploaded',
            'points': 0
        }), 400

    file = request.files['certificate']
    username = request.form.get('username', 'Unknown User')

    if file.filename == '':
        logger.error("No selected file")
        return jsonify({
            'error': 'No selected file',
            'points': 0
        }), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # Extract text from image with detailed logging
            extracted_text = extract_text_from_image(filepath)
            logger.info(f"Full Extracted Text: {extracted_text}")

            # Validate certificate
            if not validate_certificate(extracted_text):
                logger.warning("Certificate validation failed")
                return jsonify({
                    'error': 'Invalid or unrecognized certificate',
                    'points': 0
                }), 400

            # Predict points with detailed logging
            points = predict_points(extracted_text)
            logger.info(f"Points awarded: {points}")

            return jsonify({
                'username': username,
                'points': points,
                'certificateType': 'Verified Certificate'
            }), 200

        except Exception as e:
            logger.error(f"Processing error: {e}")
            return jsonify({
                'error': f'Processing error: {str(e)}',
                'points': 0
            }), 500
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)

    logger.error("Invalid file type")
    return jsonify({
        'error': 'Invalid file type',
        'points': 0
    }), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
