import cv2
import numpy as np

class StringArt:
	def __init__(self, n=200, l=1000, width=500, height=500):
		self.numPins = n
		self.numLines = l
		self.width = width
		self.height = height
		self.initPin = 0
		self.minLoop = 3
		self.lineWidth = 3
		self.lineWeight = 15
		self.coords = None
		self.lines = []
		self.imgResult = None
		self.thread_sequence = []
		
		# State variables
		self._current_line = 0
		self._previous_pins = []
		self._old_pin = None
		self._img_processed = None
		self._line_mask = None
		self._done = False

	def _invert_image(self, image):
		return 255 - image

	def _resize_image(self, img_gray):
		raise NotImplementedError

	def _process_image(self, img_sized):
		raise NotImplementedError

	def _get_pin_coords(self):
		raise NotImplementedError






	def _line_pixels(self, pin0, pin1):
		"""Bresenham's line algorithm implementation"""
		x0, y0 = int(round(pin0[0])), int(round(pin0[1]))
		x1, y1 = int(round(pin1[0])), int(round(pin1[1]))
		
		points = []
		dx = abs(x1 - x0)
		dy = abs(y1 - y0)
		x, y = x0, y0
		sx = -1 if x0 > x1 else 1
		sy = -1 if y0 > y1 else 1
		
		if dx > dy:
			err = dx / 2.0
			while x != x1:
				points.append((x, y))
				err -= dy
				if err < 0:
					y += sy
					err += dx
				x += sx
		else:
			err = dy / 2.0
			while y != y1:
				points.append((x, y))
				err -= dx
				if err < 0:
					x += sx
					err += dy
				y += sy
		
		points.append((x, y))  # Add final point
		
		# Convert to numpy arrays and clip to bounds
		if not points:
			return np.array([], dtype=int), np.array([], dtype=int)
		
		x_coords = np.array([p[0] for p in points])
		y_coords = np.array([p[1] for p in points])
		x_coords = np.clip(x_coords, 0, self.width - 1)
		y_coords = np.clip(y_coords, 0, self.height - 1)
		
		return x_coords, y_coords

	def start_generation(self, image_data):
		"""Initialize with raw image bytes"""
		image = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
		if image is None:
			raise ValueError("Could not decode image")
		
		img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
		
		img_sized = self._resize_image(img_gray)
		self._img_processed = self._process_image(img_sized)
		
		self.coords = self._get_pin_coords()
		result_height, result_width = self._img_processed.shape[:2]
		self.imgResult = 255 * np.ones((result_height, result_width))
		self._line_mask = np.zeros((result_height, result_width))
		
		self._previous_pins = []
		self._old_pin = self.initPin
		self.lines = []
		self.thread_sequence = [self._old_pin]
		self._current_line = 0
		self._done = False




	def next_step(self):
		if self._done or self._current_line >= self.numLines:
			return None, False

		old_coord = self.coords[self._old_pin]
		best_line = 0
		best_pin = self._old_pin

		for index in range(1, self.numPins):
			pin = (self._old_pin + index) % self.numPins
			coord = self.coords[pin]

			
			# Skip lines that go outside the shape (for SVG only)
			if hasattr(self, '_is_line_inside_shape') and not self._is_line_inside_shape(old_coord, coord):
				continue


			x_line, y_line = self._line_pixels(old_coord, coord)
			line_sum = np.sum(self._img_processed[y_line, x_line])

			if line_sum > best_line and pin not in self._previous_pins:
				best_line = line_sum
				best_pin = pin

		print(f"step {self._current_line + 1}: generating {self.numPins - 1} images. selected image {best_pin}")
		print("Available pins:", [pin for pin in range(self.numPins) if pin not in self._previous_pins])
		print("Best pin:", best_pin, "Score:", best_line)

		if len(self._previous_pins) >= self.minLoop:
			self._previous_pins.pop(0)
		self._previous_pins.append(best_pin)

		cv2.line(self._line_mask, old_coord, self.coords[best_pin], 
				self.lineWeight, self.lineWidth)
		self._img_processed = np.subtract(self._img_processed, self._line_mask)
		self._line_mask.fill(0)

		self.lines.append((self._old_pin, best_pin))
		self.thread_sequence.append(best_pin)
		x_line, y_line = self._line_pixels(old_coord, self.coords[best_pin])
		self.imgResult[y_line, x_line] = 0

		line_coords = (old_coord[0], old_coord[1], 
					  self.coords[best_pin][0], self.coords[best_pin][1])

		if best_pin == self._old_pin:
			self._done = True
		else:
			self._old_pin = best_pin

		self._current_line += 1
		return line_coords, not self._done












	def save_png(self, filename="output.png"):
		cv2.imwrite(filename, self.imgResult)

	def save_svg(self, filename="output.svg"):
		with open(filename, 'wb') as svg_output:
			header = f'''<?xml version="1.0" standalone="no"?>
<svg width="{self.imgResult.shape[1]}" height="{self.imgResult.shape[0]}" 
	 version="1.1" xmlns="http://www.w3.org/2000/svg">\n'''
			footer = "</svg>"
			svg_output.write(header.encode('utf8'))
			
			path = ['M' + "%i %i" % self.coords[self.lines[0][0]]]
			for l in self.lines:
				path.append("L" + "%i %i" % self.coords[l[1]])
			path.append("Z")
			
			svg_output.write(f'<path d="{" ".join(path)}" stroke="black" '
						   'stroke-width="0.5" fill="none"/>\n'.encode('utf8'))
			svg_output.write(footer.encode('utf8'))

	def save_csv(self, filename="output.csv"):
		with open(filename, 'wb') as csv_output:
			csv_output.write(b"pin_number\n")
			for pin in self.thread_sequence:
				csv_output.write(f"{pin}\n".encode('utf8'))

	def get_total_wire_length(self):
		if len(self.thread_sequence) < 2:
			return 0.0
		
		total = 0.0
		for i in range(1, len(self.thread_sequence)):
			x0, y0 = self.coords[self.thread_sequence[i-1]]
			x1, y1 = self.coords[self.thread_sequence[i]]
			total += np.hypot(x1 - x0, y1 - y0)

		return round(total, 2)
