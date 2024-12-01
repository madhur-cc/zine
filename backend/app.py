import os
from flask import Flask, request, send_file, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PIL import Image
from pdf2image import convert_from_path
import tempfile

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def pdf_to_images(pdf_path):
    try:
        # Convert the PDF to images
        images = convert_from_path(pdf_path, dpi=300)
        if len(images) != 8:
            raise ValueError("PDF must contain exactly 8 pages.")
        return images
    except Exception as e:
        raise RuntimeError(f"Error converting PDF to images: {e}")

def arrange_images(images):
    try:
        # Page order based on the corrected template
        reordered_images = [
            images[4].rotate(180),  # Page 5 (upside down)
            images[3].rotate(180),  # Page 4 (upside down)
            images[2].rotate(180),  # Page 3 (upside down)
            images[1].rotate(180),  # Page 2 (upside down)
            images[5],             # Page 6 (right side up)
            images[6],             # Page 7 (right side up)
            images[7],             # Back Cover (right side up)
            images[0],             # Front (right side up)
        ]

        # Canvas dimensions (A3 paper, 11.7" x 16.5", scaled to 300 DPI)
        canvas_width, canvas_height = 3508, 2480
        section_width, section_height = canvas_width // 4, canvas_height // 2

        # Create a blank white canvas
        canvas = Image.new("RGB", (canvas_width, canvas_height), (255, 255, 255))

        # Positions for each page on the canvas
        positions = [
            (0, 0),  # Top-left
            (section_width, 0),  # Top-second
            (section_width * 2, 0),  # Top-third
            (section_width * 3, 0),  # Top-right
            (0, section_height),  # Bottom-left
            (section_width, section_height),  # Bottom-second
            (section_width * 2, section_height),  # Bottom-third
            (section_width * 3, section_height),  # Bottom-right
        ]

        # Resize and paste each page onto the canvas
        for img, pos in zip(reordered_images, positions):
            resized_img = img.resize((section_width, section_height))
            canvas.paste(resized_img, pos)

        return canvas
    except Exception as e:
        raise RuntimeError(f"Error arranging images: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_pdf():
    if 'file' not in request.files:
        return 'No file part', 400
    
    file = request.files['file']
    
    if file.filename == '':
        return 'No selected file', 400
    
    if file and allowed_file(file.filename):
        # Save the uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Convert PDF to images
            images = pdf_to_images(filepath)
            
            # Arrange images
            zine_page = arrange_images(images)
            
            # Save the zine page to a temporary file
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'zine_output.pdf')
            zine_page.save(output_path, "PDF", resolution=300)
            
            # Send the file back to the user
            return send_file(output_path, as_attachment=True)
        
        except Exception as e:
            return str(e), 500
        finally:
            # Clean up uploaded and generated files
            if os.path.exists(filepath):
                os.remove(filepath)
            if os.path.exists('output_path'):
                os.remove('output_path')
    
    return 'Invalid file type', 400

if __name__ == '__main__':
    app.run(debug=True)
EOL