import os
import logging
import uuid
from flask import Flask, request, render_template, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from add import generate_subtitles  # Import your subtitle generation module
from os.path import basename  # Import basename function

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'subtitles'

# Configure upload and output directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Define custom filter to get basename
@app.template_filter('basename')
def get_basename(path):
    return basename(path)

# Home page with upload form
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        logging.debug("File upload request received")
        if 'file' not in request.files:
            return render_template('index.html', message='No file part')
        file = request.files['file']
        if file.filename == '':
            return render_template('index.html', message='No selected file')
        if file:
            video_language = request.form['video_language']

            # Generate a unique filename
            filename = str(uuid.uuid4()) + "_" + secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            file.save(file_path)
            logging.debug(f"Saved file: {filename}")

            try:
                # Generate subtitles
                subtitle_filename = generate_subtitles(file_path, video_language)  # Pass the full path and language
                subtitle_path = os.path.join(app.config['OUTPUT_FOLDER'], subtitle_filename)
                logging.debug(f"Generated subtitle file: {subtitle_filename}")

                # Read generated subtitles
                with open(subtitle_path, 'r', encoding='utf-8') as f:
                    subtitles = f.read()
            except Exception as e:
                logging.error(f"Error generating subtitles: {e}")
                return render_template('index.html', message='Error generating subtitles')

            return redirect(url_for('show_subtitles', subtitle_path=subtitle_path, video_path=file_path, subtitles=subtitles))

    return render_template('index.html')

# Route to show subtitles
@app.route('/show_subtitles')
def show_subtitles():
    subtitle_path = request.args.get('subtitle_path')
    video_path = request.args.get('video_path')
    subtitles = request.args.get('subtitles')

    return render_template('subtitles.html', subtitle_path=subtitle_path, video_path=video_path, subtitles=subtitles)

# Route for downloading modified subtitles
@app.route('/download_modified_subtitles/<filename>', methods=['POST'])
def download_modified_subtitles(filename):
    modified_subtitles = request.form['modified_subtitles']
    font_family = request.form['font_family']
    font_color = request.form['font_color']
    font_size = request.form['font_size']

    styled_subtitles = f"""
    <style>
        .subtitle {{
            font-family: {font_family};
            color: {font_color};
            font-size: {font_size}px;
        }}
    </style>
    <div class="subtitle">
        {modified_subtitles}
    </div>
    """

    modified_subtitle_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)

    # Write modified subtitles to file
    with open(modified_subtitle_path, 'w', encoding='utf-8') as f:
        f.write(styled_subtitles)

    # Return the modified subtitle file for download
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)
# Serve uploaded videos
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Serve generated subtitles
@app.route('/subtitles/<filename>')
def subtitles(filename):
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    subtitle_path = video_path.rsplit('.', 1)[0] + '.srt'

    # Generate subtitles using the Whisper model
    subtitles = generate_subtitles(video_path, subtitle_path)

    # Read the generated subtitles for display
    with open(subtitle_path, 'r', encoding='utf-8') as f:
        subtitles_text = f.read()

    return render_template('subtitles.html', video_path=video_path, subtitle_path=subtitle_path, subtitles=subtitles_text)

if __name__ == '__main__':
    app.run(debug=True)
