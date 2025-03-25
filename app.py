import os
import numpy as np
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
import re
import joblib
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
        text = pytesseract.image_to_string(image).lower()
        return text
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""

def predict_points(text):
    """Predict activity points based on certificate text"""
    # Keywords and their corresponding points
    certificate_patterns = {
        'nptel': 50,
        'national programme on technology enhanced learning': 50,
        'hackathon 1st': 25,
        'hackathon first': 25,
        'internship': 25,
        'workshop': 20,
        'seminar': 20,
        'conference': 20,
        'participation': 10
    }

    # Check for specific keywords
    for pattern, points in certificate_patterns.items():
        if pattern in text:
            return points
    
    # Default points for unrecognized certificates
    return 10

def validate_certificate(text):
    """Basic certificate validation"""
    # Check for typical certificate indicators
    certificate_indicators = [
        'certificate', 'participation', 'completion', 
        'awarded', 'verified', 'recognized'
    ]
    
    # Count of certificate indicators
    indicator_count = sum(1 for indicator in certificate_indicators if indicator in text)
    
    # Basic validation criteria
    is_valid = (
        len(text) > 50 and  # Minimum meaningful text length
        indicator_count > 1  # At least two certificate indicators
    )
    
    return is_valid

@app.route('/predict-points', methods=['POST'])
def upload_certificate():
    # Check if file is present
    if 'certificate' not in request.files:
        return jsonify({
            'error': 'No file uploaded',
            'points': 0
        }), 400

    file = request.files['certificate']
    username = request.form.get('username', 'Unknown User')

    # Check if filename is empty
    if file.filename == '':
        return jsonify({
            'error': 'No selected file',
            'points': 0
        }), 400

    # File validation
    if file and allowed_file(file.filename):
        # Secure filename and save
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # Extract text from image
            extracted_text = extract_text_from_image(filepath)

            # Validate certificate
            if not validate_certificate(extracted_text):
                return jsonify({
                    'error': 'Invalid or unrecognized certificate',
                    'points': 0
                }), 400

            # Predict points
            points = predict_points(extracted_text)

            # Log activity (you might want to integrate with a database)
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
