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
    """Advanced text extraction with multiple techniques and detailed logging"""
    try:
        # Open image 
        image = Image.open(file_path)
        
        # Log image details
        logger.debug(f"Image Mode: {image.mode}")
        logger.debug(f"Image Size: {image.size}")
        
        # Multiple preprocessing techniques
        preprocessing_techniques = [
            lambda img: img,  # Original image
            lambda img: img.convert('L'),  # Grayscale
            lambda img: img.convert('L').point(lambda x: 0 if x < 128 else 255, '1'),  # Binary
        ]

        extracted_texts = []
        for i, preprocess in enumerate(preprocessing_techniques):
            try:
                processed_image = preprocess(image)
                
                # Configure Tesseract with detailed configuration
                custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
                
                # Extract text with different configurations
                text = pytesseract.image_to_string(processed_image, config=custom_config)
                
                logger.debug(f"Technique {i} Raw Extracted Text: {text}")
                
                # Clean and normalize text
                clean_text = re.sub(r'\s+', ' ', text).strip().lower()
                
                if clean_text and len(clean_text) > 10:
                    extracted_texts.append(clean_text)
                    logger.debug(f"Technique {i} Cleaned Text: {clean_text}")
            
            except Exception as tech_error:
                logger.error(f"Error in preprocessing technique {i}: {tech_error}")

        # Combine unique texts
        full_text = ' '.join(set(extracted_texts))
        
        logger.debug(f"FINAL COMBINED TEXT: {full_text}")
        return full_text
    
    except Exception as e:
        logger.error(f"Comprehensive text extraction error: {e}")
        return ""

def predict_points(text):
    """Advanced points prediction with comprehensive logging"""
    logger.debug(f"FULL TEXT ANALYSIS: {text}")

    # Comprehensive NPTEL detection patterns with more flexible matching
    nptel_patterns = [
        r'national programme on technology enhanced learning',
        r'nptel',
        r'online certification',
        r'course completed',
        r'certificate of completion',
        r'online course',
        r'technology enhanced learning'
    ]

    # Enhanced pattern matching
    for pattern in nptel_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.info(f"MATCHED PATTERN: {pattern}")
            return 50

    # Additional categorization patterns
    point_categories = [
        {'patterns': [r'hackathon', r'1st prize', r'winner'], 'points': 25, 'name': 'Hackathon'},
        {'patterns': [r'internship', r'industrial training'], 'points': 25, 'name': 'Internship'},
        {'patterns': [r'workshop', r'seminar', r'conference', r'webinar'], 'points': 20, 'name': 'Professional Development'}
    ]

    # Check other point categories
    for category in point_categories:
        for pattern in category['patterns']:
            if re.search(pattern, text, re.IGNORECASE):
                logger.info(f"Matched {category['name']} category with pattern: {pattern}")
                return category['points']

    # Detailed logging for default points
    logger.warning("NO SPECIFIC CATEGORY MATCHED")
    logger.warning(f"Unmatched Text: {text}")
    return 10

@app.route('/predict-points', methods=['POST'])
def upload_certificate():
    # Existing upload and processing logic with enhanced logging
    if 'certificate' not in request.files:
        logger.error("NO FILE UPLOADED")
        return jsonify({
            'error': 'No file uploaded',
            'points': 0
        }), 400

    file = request.files['certificate']
    username = request.form.get('username', 'Unknown User')

    if file.filename == '':
        logger.error("NO SELECTED FILE")
        return jsonify({
            'error': 'No selected file',
            'points': 0
        }), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # Detailed text extraction logging
            logger.debug(f"Processing file: {filename}")
            extracted_text = extract_text_from_image(filepath)
            
            # Points prediction
            points = predict_points(extracted_text)
            
            logger.info(f"FINAL POINTS AWARDED: {points}")

            return jsonify({
                'username': username,
                'points': points,
                'certificateType': 'Verified Certificate'
            }), 200

        except Exception as e:
            logger.error(f"PROCESSING ERROR: {e}")
            return jsonify({
                'error': f'Processing error: {str(e)}',
                'points': 0
            }), 500
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)

    logger.error("INVALID FILE TYPE")
    return jsonify({
        'error': 'Invalid file type',
        'points': 0
    }), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
