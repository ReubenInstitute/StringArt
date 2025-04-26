from flask import Flask, render_template, request, flash, redirect, url_for
import cv2
import numpy as np
import base64
import os
from StringArt import OvalStringArt, RectangularStringArt

app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')
app.secret_key = 'supersecretkey'
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB limit

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
	preview_b64 = None
	img_width, img_height = None, None
	if os.path.exists('uploaded.png'):
		try:
			with open('uploaded.png', 'rb') as f:
				img_data = f.read()
				img = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)
				if img is not None:
					img_height, img_width = img.shape[:2]
					# Create preview with aspect ratio
					scale = 300 / max(img_height, img_width)
					preview_img = cv2.resize(img, (int(img_width*scale), int(img_height*scale)))
					_, buffer = cv2.imencode('.jpg', preview_img)
					preview_b64 = base64.b64encode(buffer).decode('utf-8')
		except Exception as e:
			print(f"Error loading preview: {str(e)}")
	
	return render_template('index.html', 
		uploaded_image=preview_b64,
		img_width=img_width,
		img_height=img_height
	)

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
		cv2.imwrite('uploaded.png', img)
		flash('Image uploaded successfully')
	except Exception as e:
		if os.path.exists('uploaded.png'):
			os.remove('uploaded.png')
		flash(f'Upload failed: {str(e)}')
	
	return redirect(url_for('index'))

@app.route('/generate', methods=['POST'])
def generate():
	global string_art
	
	if not os.path.exists('uploaded.png'):
		return {'error': 'No image uploaded. Please upload an image first!'}, 400

	try:
		img = cv2.imread('uploaded.png', cv2.IMREAD_COLOR)
		if img is None:
			raise ValueError("Could not read image")
		original_height, original_width = img.shape[:2]
		
		# Resize to max 500px while keeping aspect ratio
		target_size = 500
		scale = target_size / max(original_height, original_width)
		new_width = int(original_width * scale)
		new_height = int(original_height * scale)
		img_resized = cv2.resize(img, (new_width, new_height))
		
		current_frame = request.form.get('frame_type', 'circle')
		current_pins = int(request.form.get('pins', 200))
		current_lines = int(request.form.get('lines', 1000))

		if current_frame == 'circle':
			string_art = OvalStringArt(
				n=current_pins,
				l=current_lines,
				width=new_width,
				height=new_height
			)
		else:
			if current_pins % 4 != 0:
				return {'error': 'For square frame, number of pins must be divisible by 4!'}, 400
			string_art = RectangularStringArt(
				n=current_pins,
				l=current_lines,
				width=new_width,
				height=new_height
			)
		
		_, buffer = cv2.imencode('.png', img_resized)
		string_art.start_generation(buffer.tobytes())
		return {'width': new_width, 'height': new_height}, 200
	except Exception as e:
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
	if os.path.exists('uploaded.png'):
		os.remove('uploaded.png')
	return '', 204

if __name__ == '__main__':
	app.run(debug=True)