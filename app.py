import os
import re
import numpy as np
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
from flask_cors import CORS

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
    """Extract text from uploaded image using OCR"""
    try:
        image = Image.open(file_path)
        # Increase resolution for better OCR
        image = image.convert('L')  # Convert to grayscale
        text = pytesseract.image_to_string(image, lang='eng')
        return text.lower()
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""

def predict_points(text):
    """Predict activity points based on certificate text"""
    # Comprehensive keyword matching with weighted scoring
    certificate_patterns = {
        # NPTEL specific patterns
        'nptel': {
            'keywords': [
                'national programme on technology enhanced learning', 
                'nptel', 
                'online certification', 
                'completed course'
            ],
            'points': 50
        },
        # Hackathon achievements
        'hackathon': {
            'keywords': [
                'hackathon 1st', 
                'hackathon first', 
                'winner', 
                '1st prize'
            ],
            'points': 25
        },
        # Internship recognition
        'internship': {
            'keywords': [
                'internship', 
                'industrial training', 
                'work experience'
            ],
            'points': 25
        },
        # Professional development
        'professional': {
            'keywords': [
                'workshop', 
                'seminar', 
                'conference', 
                'webinar', 
                'professional development'
            ],
            'points': 20
        },
        # Participation certificates
        'participation': {
            'keywords': [
                'participation', 
                'attendee', 
                'certificate of attendance'
            ],
            'points': 10
        }
    }

    # Perform comprehensive text analysis
    for category, details in certificate_patterns.items():
        for keyword in details['keywords']:
            if keyword in text:
                return details['points']
    
    # Advanced pattern matching for NPTEL
    nptel_patterns = [
        r'national programme on technology enhanced learning',
        r'nptel online certification',
        r'course completed',
        r'certificate of completion'
    ]

    for pattern in nptel_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return 50

    # Default points
    return 10

def validate_certificate(text):
    """Advanced certificate validation"""
    # Minimum text length and meaningful content check
    if len(text) < 50:
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
    
    return indicator_count > 1

@app.route('/predict-points', methods=['POST'])
def upload_certificate():
    # File upload and processing logic remains the same as previous version
    if 'certificate' not in request.files:
        return jsonify({
            'error': 'No file uploaded',
            'points': 0
        }), 400

    file = request.files['certificate']
    username = request.form.get('username', 'Unknown User')

    if file.filename == '':
        return jsonify({
            'error': 'No selected file',
            'points': 0
        }), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # Extract text from image with improved OCR
            extracted_text = extract_text_from_image(filepath)
            print(f"Extracted Text: {extracted_text}")  # Debugging print

            # Validate certificate
            if not validate_certificate(extracted_text):
                return jsonify({
                    'error': 'Invalid or unrecognized certificate',
                    'points': 0
                }), 400

            # Predict points with enhanced logic
            points = predict_points(extracted_text)

            # Log activity
            print(f"User {username} uploaded certificate: {filename}, Points: {points}")

            return jsonify({
                'username': username,
                'points': points,
                'certificateType': 'Verified Certificate'
            }), 200

        except Exception as e:
            return jsonify({
                'error': f'Processing error: {str(e)}',
                'points': 0
            }), 500
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)

    return jsonify({
        'error': 'Invalid file type',
        'points': 0
    }), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
