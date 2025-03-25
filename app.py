import os
import re
import logging
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

def extract_text_from_image(file_path):
    """Advanced text extraction with multiple techniques"""
    try:
        image = Image.open(file_path)
        
        # Multiple preprocessing techniques
        text_variants = []
        
        # Original image
        text_variants.append(pytesseract.image_to_string(image).lower())
        
        # Grayscale
        gray_image = image.convert('L')
        text_variants.append(pytesseract.image_to_string(gray_image).lower())
        
        # Binary image
        binary_image = gray_image.point(lambda x: 0 if x < 128 else 255, '1')
        text_variants.append(pytesseract.image_to_string(binary_image).lower())
        
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

    # NPTEL specific patterns
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

    # Other point categories
    point_categories = [
        {'patterns': [r'hackathon', r'1st prize', r'winner'], 'points': 25},
        {'patterns': [r'internship', r'industrial training'], 'points': 25},
        {'patterns': [r'workshop', r'seminar', r'conference', r'webinar'], 'points': 20}
    ]

    # Check other categories
    for category in point_categories:
        for pattern in category['patterns']:
            if re.search(pattern, text, re.IGNORECASE):
                logger.info(f"Matched category: {pattern}")
                return category['points']

    # Default points
    logger.warning("No specific category matched")
    return 10

@app.route('/predict-points', methods=['POST'])
def upload_certificate():
    """Certificate points prediction endpoint"""
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
            # Extract text from image
            extracted_text = extract_text_from_image(filepath)
            logger.info(f"Full Extracted Text: {extracted_text}")

            # Predict points
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
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
