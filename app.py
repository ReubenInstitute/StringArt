from flask import Flask, render_template, request, flash, redirect, url_for
import cv2
import numpy as np
import base64
import os
from werkzeug.utils import secure_filename
from OvalStringArt import OvalStringArt
from RectangularStringArt import RectangularStringArt
from OctagonStringArt import OctagonStringArt
from SVGStringArt import SVGStringArt


app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')
app.secret_key = 'supersecretkey'
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB limit

UPLOAD_DIR = 'upload'
os.makedirs(UPLOAD_DIR, exist_ok=True)

SVG_DIR = 'svg'

def list_svg_shapes():
	"""Basenames (no .svg) of the shape files in SVG_DIR, for the frame-type list."""
	return sorted(os.path.splitext(f)[0] for f in os.listdir(SVG_DIR) if f.endswith('.svg'))

string_art = None

def validate_image(file_stream):
	try:
		img = cv2.imdecode(np.frombuffer(file_stream.read(), np.uint8), cv2.IMREAD_COLOR)
		if img is None:
			raise ValueError("Invalid image format")
		return img
	except Exception as e:
		raise ValueError("Error processing image") from e

@app.route('/', methods=['GET'])
def index():
	uploaded_files = sorted(os.listdir(UPLOAD_DIR))
	svg_shapes = list_svg_shapes()
	return render_template('index.html', uploaded_files=uploaded_files, svg_shapes=svg_shapes)

@app.route('/upload', methods=['POST'])
def handle_upload():
	if 'image' not in request.files:
		flash('No file selected')
		return redirect(url_for('index'))

	file = request.files['image']
	if file.filename == '':
		flash('No selected file')
		return redirect(url_for('index'))

	try:
		img = validate_image(file.stream)
		filename = secure_filename(file.filename)
		cv2.imwrite(os.path.join(UPLOAD_DIR, filename), img)
		flash('Image uploaded successfully')
	except Exception as e:
		flash(f'Upload failed: {str(e)}')

	return redirect(url_for('index'))


@app.route('/generate', methods=['POST'])
def generate():
	global string_art
	
	selected_file = request.form.get('selected_file', '')
	image_path = os.path.join(UPLOAD_DIR, secure_filename(selected_file))
	if not selected_file or not os.path.exists(image_path):
		return {'error': 'No image selected. Please upload and select an image first!'}, 400

	try:
		img = cv2.imread(image_path, cv2.IMREAD_COLOR)
		if img is None:
			raise ValueError("Could not read image")
		original_height, original_width = img.shape[:2]


		# Get size from form data
		target_size = int(request.form.get('size', 400))
		if target_size < 100 or target_size > 2000:
			target_size = 400  # default if invalid

		# The frame (circle/square/octagon/SVG) is always a fixed square shape,
		# so the canvas must be square too. Center-crop the photo to a square
		# first (losing whatever doesn't fit), then resize it onto that canvas.
		crop_size = min(original_height, original_width)
		top = (original_height - crop_size) // 2
		left = (original_width - crop_size) // 2
		img_cropped = img[top:top + crop_size, left:left + crop_size]

		new_width = new_height = target_size
		img_resized = cv2.resize(img_cropped, (new_width, new_height))

		current_frame = request.form.get('frame_type', 'circle')
		current_pins = int(request.form.get('pins', 200))
		current_lines = int(request.form.get('lines', 1000))

		# Frame type handling
		if current_frame == 'circle':
			string_art = OvalStringArt(
				n=current_pins,
				l=current_lines,
				width=new_width,
				height=new_height
			)
		elif current_frame == 'square':
			if current_pins % 4 != 0:
				return {'error': 'For square frame, number of pins must be divisible by 4!'}, 400
			string_art = RectangularStringArt(
				n=current_pins,
				l=current_lines,
				width=new_width,
				height=new_height
			)
		elif current_frame == 'octagon':
			if current_pins % 8 != 0:
				return {'error': 'For octagon frame, number of pins must be divisible by 8!'}, 400
			string_art = OctagonStringArt(
				n=current_pins,
				l=current_lines,
				width=new_width,
				height=new_height
			)
		elif current_frame in list_svg_shapes():
			# SVG path handling - no pin constraints
			svg_path = os.path.join(SVG_DIR, secure_filename(current_frame) + '.svg')
			string_art = SVGStringArt(
				n=current_pins,
				l=current_lines,
				width=new_width,
				height=new_height,
				svg_file=svg_path
			)
		else:
			return {'error': 'Invalid frame type selected'}, 400
		
		# Common initialization for all frame types
		_, buffer = cv2.imencode('.png', img_resized)
		string_art.start_generation(buffer.tobytes())

		# Get processed image and invert back to original within mask
		processed_img = string_art._img_processed.copy()
		processed_img = 255 - processed_img  # Invert to show original within mask

		# Convert to 3 channels if grayscale
		if len(processed_img.shape) == 2:
			processed_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2BGR)


		# In the generate route, after getting the processed_img:
		processed_img = string_art._img_processed.copy()
		processed_img = 255 - processed_img  # Invert to show original within mask

		# Convert to 3 channels if grayscale
		if len(processed_img.shape) == 2:
 			processed_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2BGR)

		# Add pin markers ONLY to preview image
		for (x, y) in string_art.coords:
			cv2.circle(processed_img, (x, y), radius=3, color=(0, 0, 255), thickness=-1)

		# Resize for preview
		scale = 300 / max(new_height, new_width)
		preview_processed = cv2.resize(processed_img, (int(new_width * scale), int(new_height * scale)))

		# Encode to base64
		_, buffer = cv2.imencode('.jpg', preview_processed)
		processed_b64 = base64.b64encode(buffer).decode('utf-8')

		return {'width': new_width, 'height': new_height, 'processed_image': processed_b64}, 200
	except Exception as e:
		app.logger.error(f"Generation failed: {str(e)}", exc_info=True)
		return {'error': str(e)}, 400




@app.route('/next_step')
def next_step():
	global string_art
	if string_art is None:
		return {'done': True}, 400
	
	line_coords, has_more = string_art.next_step()
	if line_coords is None:
		return {'done': True}
	
	current_step = int(string_art._current_line)
	wire_length = float(string_art.get_total_wire_length() / 1000)
	
	return {
		'x0': int(line_coords[0]),
		'y0': int(line_coords[1]),
		'x1': int(line_coords[2]),
		'y1': int(line_coords[3]),
		'done': not has_more,
		'step': current_step,
		'length': round(wire_length, 2)
	}

@app.route('/reset')
def reset():
	global string_art
	string_art = None
	return '', 204

if __name__ == '__main__':
	app.run(debug=True)
