#!/usr/bin/env python

import sys
import os
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
		length = int(np.hypot(pin1[0] - pin0[0], pin1[1] - pin0[1]))
		x = np.linspace(pin0[0], pin1[0], length).astype(int)
		y = np.linspace(pin0[1], pin1[1], length).astype(int)
		return (x-1, y-1)

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
			x_line, y_line = self._line_pixels(old_coord, coord)
			line_sum = np.sum(self._img_processed[y_line, x_line])
			
			if line_sum > best_line and pin not in self._previous_pins:
				best_line = line_sum
				best_pin = pin

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


class OvalStringArt(StringArt):
	def _resize_image(self, img_gray):
		return cv2.resize(img_gray, (self.width, self.height))

	def _process_image(self, img_sized):
		img_inverted = self._invert_image(img_sized)
		center_x, center_y = self.width // 2, self.height // 2
		a, b = center_x, center_y
		
		y, x = np.ogrid[:self.height, :self.width]
		mask = ((x - center_x)/a)**2 + ((y - center_y)/b)**2 > 1
		img_inverted[mask] = 0
		return img_inverted

	def _get_pin_coords(self):
		alpha = np.linspace(0, 2 * np.pi, self.numPins + 1)[:-1]
		center_x, center_y = self.width // 2, self.height // 2
		a, b = center_x, center_y
		return [
			(int(center_x + a * np.cos(angle)), 
			int(center_y + b * np.sin(angle))) 
			for angle in alpha
		]


class RectangularStringArt(StringArt):
	def __init__(self, n=200, l=1000, width=500, height=500):
		super().__init__(n, l, width, height)

	def _get_pin_coords(self):
		width = self.width
		height = self.height
		num_pins = self.numPins
		perimeter = 2 * (width + height)
		step = perimeter / num_pins  # Distance between pins
		
		coords = []
		for i in range(num_pins):
			pos = i * step  # Current position along perimeter
			
			# Top side (left to right)
			if pos < width:
				x = pos
				y = 0
			# Right side (top to bottom)
			elif pos < width + height:
				x = width
				y = pos - width
			# Bottom side (right to left)
			elif pos < 2 * width + height:
				x = width - (pos - (width + height))
				y = height
			# Left side (bottom to top)
			else:
				x = 0
				y = height - (pos - (2 * width + height))
			
			coords.append((int(x), int(y)))
		
		return coords

	def _resize_image(self, img_gray):
		return cv2.resize(img_gray, (self.width, self.height))

	def _process_image(self, img_sized):
		return self._invert_image(img_sized)


class OctagonStringArt(StringArt):
	def _resize_image(self, img_gray):
		return cv2.resize(img_gray, (self.width, self.height))

	def _process_image(self, img_sized):
		img_inverted = self._invert_image(img_sized)
		
		# Create octagonal mask
		vertices = self._get_octagon_vertices()
		mask = np.zeros_like(img_inverted)
		cv2.fillPoly(mask, [np.array(vertices)], 255)
		
		# Apply mask and return
		return cv2.bitwise_and(img_inverted, mask)

	def _get_octagon_vertices(self):
		w, h = self.width, self.height
		cut_x = int(w * 0.2)  # 20% cutoff from width
		cut_y = int(h * 0.2)  # 20% cutoff from height
		return [
			(cut_x, 0),		  # Top-left
			(w - cut_x, 0),	  # Top-right
			(w, cut_y),		  # Right-top
			(w, h - cut_y),	  # Right-bottom
			(w - cut_x, h),	  # Bottom-right
			(cut_x, h),		  # Bottom-left
			(0, h - cut_y),	  # Left-bottom
			(0, cut_y)		   # Left-top
		]

	def _get_pin_coords(self):
		vertices = self._get_octagon_vertices()
		coords = []
		total_pins = self.numPins
		
		# Calculate pins per side with remainder distribution
		base_pins, remainder = divmod(total_pins, 8)
		
		for side in range(8):
			# Get current and next vertex
			start = vertices[side]
			end = vertices[(side + 1) % 8]
			
			# Calculate pins for this side
			pins_this_side = base_pins + (1 if side < remainder else 0)
			
			# Generate coordinates along the edge
			x = np.linspace(start[0], end[0], pins_this_side + 1)[:-1]
			y = np.linspace(start[1], end[1], pins_this_side + 1)[:-1]
			coords.extend(zip(x.astype(int), y.astype(int)))

		return coords[:total_pins]  # Ensure exact count

if __name__ == "__main__":
	# Standalone demo (works with input.jpg)
	if os.path.exists("input.jpg"):
		with open("input.jpg", "rb") as f:
			image_data = f.read()
		
		rectangle = RectangularStringArt(n=200, l=4000, width=500, height=500)
		rectangle.start_generation(image_data)
		
		while rectangle.next_step()[1]:
			sys.stdout.write(f"\r[+] Computing line {rectangle._current_line} of {rectangle.numLines}")
			sys.stdout.flush()
		
		rectangle.save_png()
		rectangle.save_svg()
		rectangle.save_csv()
		print(f"\nTotal wire length: {rectangle.get_total_wire_length()} mm")
	else:
		print("Error: input.jpg not found for standalone execution")