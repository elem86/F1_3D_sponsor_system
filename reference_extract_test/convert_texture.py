from pathlib import Path

from PIL import Image

script_dir = Path(__file__).resolve().parent
input_file = script_dir / "mcltexm2.ppm"
output_file = script_dir / "mcltexm2.png"

with Image.open(input_file) as image:
    image.save(output_file)
    texture_size = image.size

print(f"Converted {input_file} -> {output_file}")
print(f"Texture size: {texture_size}")
