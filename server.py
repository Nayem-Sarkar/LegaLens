import os
import tempfile
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from main import process_file

app = Flask(__name__, static_url_path='', static_folder='.')

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    # 1. Handle Pasted Text
    if 'text' in request.form:
        text_content = request.form['text']
        if not text_content.strip():
            return jsonify({"error": "No text provided"}), 400
            
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'pasted_text.txt')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text_content)
            
        try:
            report = process_file(filepath)
            os.remove(filepath)
            return jsonify(report)
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({"error": str(e)}), 500

    # 2. Handle File Uploads
    if 'file' not in request.files:
        return jsonify({"error": "No file or text part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Process the file using our core logic
            report = process_file(filepath)
            
            # Clean up temp file
            os.remove(filepath)
            
            return jsonify(report)
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({"error": str(e)}), 500
            
    return jsonify({"error": "File type not allowed. Please upload TXT, PDF, or Images."}), 400

if __name__ == '__main__':
    print("Starting LegaLens Web Server on http://0.0.0.0:8080")
    app.run(host='0.0.0.0', port=8080, debug=True)
