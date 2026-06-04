# Image Meta Data Manipulator

Strip AI metadata from images (DALL-E, Midjourney, Stable Diffusion, ComfyUI, etc.) and optionally inject realistic camera EXIF or Canva metadata.

## Installation

```bash
pip install git+https://github.com/fahimpyto/image-meta-data-manipulator.git
```

After installation, the `metascrub` command is available globally from any terminal.

To update:

```bash
pip install --upgrade git+https://github.com/fahimpyto/image-meta-data-manipulator.git
```

## Usage

```bash
# Scan a folder for AI-generated images
metascrub scan

# Scan recursively
metascrub scan -r

# Interactive mode — select files to clean and inject metadata
metascrub scan -i

# Show metadata for a single image
metascrub info image.png

# Strip AI metadata from an image
metascrub clean image.png

# Clean and inject realistic camera EXIF
metascrub clean image.png --organic

# Batch clean all images in a directory
metascrub clean -p . -r
```

## Commands

| Command   | Description                                   |
|-----------|-----------------------------------------------|
| `scan`    | Scan folder for images with AI metadata       |
| `info`    | Show detailed metadata for a single image     |
| `clean`   | Strip AI metadata from images                 |

## Interactive Mode

```
metascrub scan -i
```

1. Scans the folder and shows all images with AI / Canva metadata
2. Select files by number (e.g. `1,3,5`, `1-5`, or Enter for all)
3. Enter an output folder name (or press Enter for in-place)
4. For each file:
   - Cleans AI metadata
   - Prompts: (s)kip / (a)uto EXIF / (p)ersonalize / (c)anva

## Supported Formats

- JPEG / JPG
- PNG
- WebP
