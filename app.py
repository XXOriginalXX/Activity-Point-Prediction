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

def convert_pdf_to_images(pdf_path, output_folder):
    """Convert PDF to images for OCR processing"""
    try:
        # Convert PDF to images
        images = pdf2image.convert_from_path(
            pdf_path, 
            dpi=300,  # Higher DPI for better text recognition
            output_folder=output_folder,
            fmt='jpg',
            # Limit to first 3 pages to prevent processing very large PDFs
            first_page=1,
            last_page=3  
        )
        return images
    except Exception as e:
        logger.error(f"PDF conversion error: {e}")
        return []

def extract_text_from_images(images):
    """Extract text from a list of images"""
    extracted_texts = []
    
    for image in images:
        try:
            # Convert PIL Image to grayscale
            gray_image = image.convert('L')
            
            # Apply thresholding
            binary_image = gray_image.point(lambda x: 0 if x < 128 else 255, '1')
            
            # Extract text with Tesseract
            text = pytesseract.image_to_string(
                binary_image, 
                config='--psm 6 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.() '
            ).lower()
            
            if text.strip():
                extracted_texts.append(text)
        except Exception as e:
            logger.error(f"Text extraction error: {e}")
    
    # Combine texts
    full_text = ' '.join(extracted_texts)
    logger.debug(f"Extracted Text: {full_text}")
    return full_text

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
    filename = data.get('filename', 'certificate')
    base64_data = data['certificate']

    try:
        # Remove data URL prefix if present
        if base64_data.startswith('data:'):
            base64_data = base64_data.split(',')[1]

        # Decode base64
        file_data = base64.b64decode(base64_data)
        
        # Determine file type
        import magic
        mime_type = magic.from_buffer(file_data, mime=True)
        logger.info(f"Detected MIME type: {mime_type}")

        # Save temporary file
        file_extension = mime_type.split('/')[-1]
        if file_extension == 'pdf':
            file_extension = 'pdf'
        elif file_extension in ['jpeg', 'png', 'jpg']:
            file_extension = file_extension
        else:
            return jsonify({
                'error': f'Unsupported file type: {mime_type}',
                'points': 0
            }), 400

        temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 
                                     f"{secure_filename(filename)}.{file_extension}")
        
        with open(temp_filepath, 'wb') as f:
            f.write(file_data)

        try:
            # Process different file types
            if file_extension == 'pdf':
                # Convert PDF to images
                images = convert_pdf_to_images(temp_filepath, app.config['UPLOAD_FOLDER'])
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
            for f in os.listdir(app.config['UPLOAD_FOLDER']):
                if f.endswith('.jpg'):
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))

    except Exception as e:
        logger.error(f"Base64 decoding error: {e}")
        return jsonify({
            'error': 'Invalid file format',
            'points': 0
        }), 400

if __name__ == '__main__':
    # Run the Flask app
    app.run(
        host='0.0.0.0', 
        port=int(os.environ.get('PORT', 5000)),
        debug=True
    )

# Additional requirements (beyond previous requirements):
# python-magic
# pdf2image
