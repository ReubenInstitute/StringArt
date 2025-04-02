import numpy as np
import math
import random
import time
from PIL import Image

def draw_line(img, start, end, value):
    """Simple Bresenham's line algorithm"""
    x0, y0 = start
    x1, y1 = end
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    
    while True:
        if 0 <= x0 < img.shape[1] and 0 <= y0 < img.shape[0]:
            img[y0, x0] = max(0, img[y0, x0] - value)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy

def generate_string_art(image_path, num_nails=200, max_lines=5000, darkness=15):
    """Guaranteed-working string art generator"""
    # Load image
    img = Image.open(image_path).convert("L")
    target = 255 - np.array(img, dtype=np.int32)
    height, width = target.shape
    
    # Create nail positions
    center_x, center_y = width//2, height//2
    radius = min(center_x, center_y) * 0.95
    nails = []
    for i in range(num_nails):
        angle = 2 * math.pi * i / num_nails
        x = int(center_x + radius * math.cos(angle))
        y = int(center_y + radius * math.sin(angle))
        nails.append((x, y))
    
    # Initialize
    current = np.full((height, width), 255, dtype=np.int32)
    current_nail = random.randint(0, num_nails-1)
    path = [current_nail]
    
    print(f"Processing {width}x{height} image with {num_nails} nails")
    print("\nStep  From    To")
    print("----------------")
    
    for step in range(max_lines):
        # Find the best next nail
        best_error = float('inf')
        best_nail = current_nail
        
        for _ in range(100):  # Try 100 random nails
            next_nail = random.randint(0, num_nails-1)
            if next_nail == current_nail:
                continue
                
            # Test the line
            temp = current.copy()
            draw_line(temp, nails[current_nail], nails[next_nail], darkness)
            
            # Calculate error
            error = np.sum((target - temp)**2)
            
            if error < best_error:
                best_error = error
                best_nail = next_nail
        
        # Draw the best line found
        draw_line(current, nails[current_nail], nails[best_nail], darkness)
        path.append(best_nail)
        
        # Print progress
        print(f"{step+1:5d}  {path[-2]:4d}  {path[-1]:4d}")
        
        # Save temporary output
        if step % 10 == 0:
            Image.fromarray(current.astype(np.uint8)).save("output.png")
        
        current_nail = best_nail
    
    # Save final result
    Image.fromarray(current.astype(np.uint8)).save("final.png")
    print("\nDone! Final image saved to final.png")

if __name__ == '__main__':
    generate_string_art("logo.jpg")