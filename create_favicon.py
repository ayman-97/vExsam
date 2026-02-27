"""Generate a favicon for the Virtual National Exam app."""
from PIL import Image, ImageDraw

img = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Blue circle background
draw.ellipse([4, 4, 124, 124], fill='#1a56db', outline='#ffffff', width=3)

# White paper/document
draw.rounded_rectangle([35, 22, 93, 102], radius=5, fill='white')

# Blue checkmark
draw.line([(48, 62), (58, 76), (82, 42)], fill='#1a56db', width=6, joint='curve')

# Grey lines (text representation)
draw.line([(45, 85), (83, 85)], fill='#b0b0b0', width=3)
draw.line([(45, 93), (73, 93)], fill='#b0b0b0', width=2)

img.save('favicon.png')
print("favicon.png created!")
