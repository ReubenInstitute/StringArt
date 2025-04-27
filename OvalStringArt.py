from StringArt import StringArt
import cv2
import numpy as np

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
