import numpy as np
import math
import random
import time
import os
from PIL import Image

def draw_line(img, start, end, value):
    """Bresenham's line algorithm with bounds checking"""
    x0, y0 = start
    x1, y1 = end
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    
    pixels = []
    while True:
        if 0 <= x0 < img.shape[1] and 0 <= y0 < img.shape[0]:
            img[y0, x0] = max(0, img[y0, x0] - value)
            pixels.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return pixels

def generate_string_art(image_path, num_nails=300, max_lines=5000, darkness=10):
    """Continuous wire string art with step-by-step output"""
    # Load image
    img = Image.open(image_path).convert("L")
    target = 255 - np.array(img, dtype=np.int64)
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
    
    # Initialize canvas
    current = np.full((height, width), 255, dtype=np.int64)
    current_nail = random.randint(0, num_nails-1)
    path = [current_nail]
    
    print(f"Processing {width}x{height} image with {num_nails} nails")
    print("\nStep   From     To   Time (s)   Current Error")
    print("--------------------------------------------")
    start_time = time.time()
    
    # Create output directory
    os.makedirs("progress", exist_ok=True)
    
    for step in range(max_lines):
        step_start = time.time()
        best_error = float('inf')
        best_nail = None
        
        # Try connections from current nail
        for _ in range(100):
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
        
        if best_nail is None:
            print("No improving connections found - stopping early")
            break
            
        # Apply the best line
        draw_line(current, nails[current_nail], nails[best_nail], darkness)
        path.append(best_nail)
        
        # Calculate metrics
        current_error = np.sum((target - current)**2)
        step_time = time.time() - step_start
        
        # Save temporary image (overwrites each step)
        temp_img = Image.fromarray(current.astype(np.uint8))
        temp_img.save("output.png")  # Main output file
        temp_img.save(f"progress/step_{step+1:05d}.png")  # Archive
        
        # Progress reporting
        print(f"{step+1:5d}  {path[-2]:4d}    {path[-1]:4d}  {step_time:7.3f}  {current_error:15,.0f}")
        
        current_nail = best_nail
    
    # Save final outputs
    final_img = Image.fromarray(current.astype(np.uint8))
    final_img.save("string_art_final.png")
    
    with open("nail_path.txt", "w") as f:
        f.write("\n".join(map(str, path)))
    
    total_time = time.time() - start_time
    print("\nCompleted in {:.1f} seconds".format(total_time))
    print(f"Final error: {current_error:,.0f}")
    print("Final image saved to string_art_final.png")
    print("Temporary outputs saved to output.png (overwritten each step)")
    print("Step-by-step images saved to progress/ directory")

if __name__ == '__main__':
    generate_string_art("logo.jpg", num_nails=300, max_lines=5000, darkness=12)