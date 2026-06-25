#!/usr/bin/env python3
"""
Generate PWA icon sizes from a single source image.
Usage: python generate_icons.py --source path/to/image.png --output static/
"""

import os
import argparse
from PIL import Image

# Required sizes for the manifest (in pixels)
ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

def generate_icons(source_path, output_dir="static"):
    """
    Resize source image to all required icon sizes and save them.
    """
    if not os.path.exists(source_path):
        print(f"Error: Source image '{source_path}' not found.")
        return False

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    try:
        img = Image.open(source_path)
        # Convert to RGBA if necessary (preserve transparency)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Optional: resize with a high-quality filter
        for size in ICON_SIZES:
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            filename = f"icon-{size}.png"
            filepath = os.path.join(output_dir, filename)
            resized.save(filepath, format='PNG')
            print(f"Generated {filename} ({size}x{size})")

        print(f"\n✅ All icons generated successfully in '{output_dir}'.")
        return True

    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate PWA icons")
    parser.add_argument("--source", required=True, help="Path to source image (e.g., icon-base.png)")
    parser.add_argument("--output", default="static", help="Output directory (default: static)")
    args = parser.parse_args()

    generate_icons(args.source, args.output)