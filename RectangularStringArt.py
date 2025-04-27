from StringArt import StringArt
import cv2
import numpy as np

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
