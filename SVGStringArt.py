from StringArt import StringArt
import os
import cv2
import numpy as np
from svgpathtools import svg2paths2

class SVGStringArt(StringArt):
	def __init__(self, n=200, l=1000, width=500, height=500, svg_file="svg/shape.svg"):
		super().__init__(n, l, width, height)
		self.svg_path = None
		self._total_length = 0
		self.original_svg_width = 1
		self.original_svg_height = 1
		self.mask = None

		# Load and parse SVG file
		if not os.path.exists(svg_file):
			raise FileNotFoundError(f"Required SVG file not found: {svg_file}")
			
		try:
			# Get SVG metadata including viewBox
			paths, _, svg_attrs = svg2paths2(svg_file)
			if len(paths) != 1:
				raise ValueError(f"{svg_file} must contain exactly one path")
				
			self.svg_path = paths[0]
			if not self.svg_path.isclosed():
				raise ValueError(f"Path in {svg_file} must be closed")

			# Extract viewBox dimensions
			view_box = svg_attrs.get('viewBox', '0 0 512 512').split()
			if len(view_box) < 4:
				view_box = [0, 0, 512, 512]  # Fallback to default
				
			self.original_svg_width = float(view_box[2]) or 512
			self.original_svg_height = float(view_box[3]) or 512
			
			self._total_length = self.svg_path.length()
			self._generate_mask()  # Generate mask after loading path

		except Exception as e:
			raise RuntimeError(f"Failed to load {svg_file}: {str(e)}")


	def _generate_mask(self):
		"""Create binary mask of the SVG shape"""
		self.mask = np.zeros((self.height, self.width), dtype=np.uint8)
		scale_x = self.width / self.original_svg_width
		scale_y = self.height / self.original_svg_height
	
		# Create path points with consistent rounding
		points = []
		for t in np.linspace(0, 1, 5000):
			point = self.svg_path.point(t)
			x = int(round(point.real * scale_x))
			y = int(round(point.imag * scale_y))
			x = max(0, min(x, self.width-1))
			y = max(0, min(y, self.height-1))
			points.append((x, y))
	
		if points:
			cv2.polylines(self.mask, [np.array(points)], isClosed=True, color=255, thickness=1)
			contours, _ = cv2.findContours(self.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
			cv2.drawContours(self.mask, contours, -1, 255, thickness=cv2.FILLED)


	def _old_generate_mask(self):
		"""Create binary mask of the SVG shape"""
		self.mask = np.zeros((self.height, self.width), dtype=np.uint8)
		scale_x = self.width / self.original_svg_width
		scale_y = self.height / self.original_svg_height

		# Create path points
		points = []
		for t in np.linspace(0, 1, 5000):  # High-resolution sampling
			point = self.svg_path.point(t)
			x = int(round(point.real * scale_x))
			y = int(round(point.imag * scale_y))
			x = max(0, min(x, self.width-1))
			y = max(0, min(y, self.height-1))
			points.append((x, y))

		# Draw and fill polygon
		if points:
			cv2.polylines(self.mask, [np.array(points)], isClosed=True, color=255, thickness=1)
			contours, _ = cv2.findContours(self.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
			cv2.drawContours(self.mask, contours, -1, 255, thickness=cv2.FILLED)


	def _get_pin_coords(self):
		"""Evenly distribute pins along the SVG path"""
		# Calculate the total length of the path
		total_length = self.svg_path.length()
		
		# Calculate positions for each pin
		coords = []
		for i in range(self.numPins):
			# Get the position along the path (0-1)
			t = i / self.numPins
			
			# Get the point at this position
			point = self.svg_path.point(t)
			
			# Scale to our target dimensions
			x = int((point.real / self.original_svg_width) * self.width)
			y = int((point.imag / self.original_svg_height) * self.height)
			
			# Clamp to image bounds
			x = max(0, min(x, self.width - 1))
			y = max(0, min(y, self.height - 1))
			
			coords.append((x, y))
		
		return coords

	def _length_to_point(self, target_length: float):
		"""Convert arc length to scaled coordinates with clamping"""
		# Normalize target length
		t = target_length / self._total_length
		
		# Get the point
		point = self.svg_path.point(t)
		
		# Scale and clamp coordinates
		x = int((point.real / self.original_svg_width) * self.width)
		y = int((point.imag / self.original_svg_height) * self.height)
		return (
			max(0, min(x, self.width - 1)),
			max(0, min(y, self.height - 1))
		)

	def _is_line_inside_shape(self, p1, p2):
		"""Precisely check if all pixels of a line stay inside the shape"""
		# Generate all pixel coordinates along the line
		x_line, y_line = self._line_pixels(p1, p2)
		
		# Check all pixels are within the mask
		mask_vals = self.mask[y_line, x_line]
		return np.all(mask_vals > 0)
	
	def _resize_image(self, img_gray):
		return cv2.resize(img_gray, (self.width, self.height))
	
	def _process_image(self, img_sized):
		img_inverted = self._invert_image(img_sized)
		return cv2.bitwise_and(img_inverted, img_inverted, mask=self.mask)
