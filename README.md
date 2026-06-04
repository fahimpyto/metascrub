# Image Meta Data Manipulator

Strip AI metadata from images (DALL-E, Midjourney, Stable Diffusion, ComfyUI, etc.) and optionally inject realistic camera EXIF.

## Installation

```bash
pip install -e metascrub/
```

Or use the pre-built `metascrub.exe` directly.

## Usage

```bash
# Scan a folder for AI-generated images
metascrub scan

# Scan recursively
metascrub scan -r

# Show metadata for a single image
metascrub info image.png

# Strip AI metadata from an image
metascrub clean image.png

# Dry run — preview what would be cleaned
metascrub clean --dry-run

# Clean and inject realistic camera EXIF
metascrub clean image.png --organic

# Batch clean all images in a directory
metascrub clean -p . -r
```

### Using the `.exe` (Windows)

```bash
.\metascrub scan
.\metascrub info image.png
.\metascrub clean image.png
```

## Commands

| Command   | Description                                   |
|-----------|-----------------------------------------------|
| `scan`    | Scan folder for images with AI metadata       |
| `info`    | Show detailed metadata for a single image     |
| `clean`   | Strip AI metadata from images                 |

## Supported Formats

- JPEG / JPG
- PNG
- WebP
