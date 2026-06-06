[![PyPI version](https://img.shields.io/pypi/v/metascrub)](https://pypi.org/project/metascrub/)
[![Python versions](https://img.shields.io/pypi/pyversions/metascrub)](https://pypi.org/project/metascrub/)
[![License](https://img.shields.io/pypi/l/metascrub)](https://github.com/fahimpyto/image-meta-data-manipulator/blob/main/LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-fahimpyto%2Fimage--meta--data--manipulator-blue)](https://github.com/fahimpyto/image-meta-data-manipulator)

```
███╗   ███╗███████╗████████╗ █████╗ ███████╗ ██████╗██████╗ ██╗   ██╗██████╗
████╗ ████║██╔════╝╚══██╔══╝██╔══██╗██╔════╝██╔════╝██╔══██╗██║   ██║██╔══██╗
██╔████╔██║█████╗     ██║   ███████║███████╗██║     ██████╔╝██║   ██║██████╔╝
██║╚██╔╝██║██╔══╝     ██║   ██╔══██║╚════██║██║     ██╔══██╗██║   ██║██╔══██╗
██║ ╚═╝ ██║███████╗   ██║   ██║  ██║███████║╚██████╗██║  ██║╚██████╔╝██████╔╝
╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝
```

**Strip AI metadata from images** — ChatGPT, DALL-E, Midjourney, Stable Diffusion, ComfyUI, Adobe Firefly, and more. Optionally inject realistic camera EXIF or design-app metadata.

---

## 📦 Installation

```bash
pip install metascrub
```

After installation, the `mtsb` command is available globally from any terminal.

To update:

```bash
pip install --upgrade metascrub
```

## 🚀 Quick Start

```bash
# Check if an image is AI-generated
mtsb status image.png

# Strip all AI metadata
mtsb clean image.png

# Strip + inject realistic camera EXIF
mtsb clean image.png --organic

# Strip + inject design-app metadata
mtsb clean image.png --design
```

## 📋 Commands

| Command   | Description                                           |
|-----------|-------------------------------------------------------|
| `scan`    | Scan folder interactively — pick images to process    |
| `info`    | Show ALL metadata for an image (full details)         |
| `status`  | Quick check: is this image AI-generated?              |
| `clean`   | Strip AI metadata and save to output folder           |

## 💻 Usage

```bash
# Interactive scan — shows numbered table, pick an image, then choose action
mtsb scan

# Show ALL metadata (50+ fields: AI, C2PA manifest, EXIF, PNG chunks, etc.)
mtsb info image.png

# Quick check — AI or not?
mtsb status image.png

# Strip AI metadata — always saves to output/ folder
mtsb clean image.png

# Clean with custom output name
mtsb clean image.png -n my_clean_image

# Clean + inject realistic camera EXIF
mtsb clean image.png --organic

# Clean + inject design-app metadata (Photoshop/Procreate style)
mtsb clean image.png --design
```

### ⌨️ Interactive Scan Flow

```
> mtsb scan
  # │ File                  │ AI?  │ Tool
  ───┼──────────────────────┼──────┼─────────────
  1  │ ChatGPT ...png       │ YES  │ ChatGPT (OpenAI)
  2  │ DSC00065.jpg         │ NO   │ —
  3  │ ai_art.png           │ YES  │ Midjourney

  Select # (or 'a' all, 'q' quit): 1

  ── image.png ──
  [1] Info — show ALL metadata
  [2] Clean — strip AI metadata → output/ folder
  [3] Data Manipulate
       [A] Auto Organic — inject realistic camera EXIF
       [C] Custom Edit — type all fields (make, model, GPS, etc.)
       [D] Add Design App — Photoshop/Procreate/Canva style
  [4] Back to scan results
  [5] Exit
```

**Navigation tips:**
- Type **`b`** or **`c`** at any filename prompt to cancel and return to the previous menu
- Press **`Ctrl+C`** at any prompt to cancel and go back
- Press **`q`** at the scan selection to exit entirely

## ✨ Features

### 🔍 Deep C2PA Manifest Parsing
Images from ChatGPT, DALL-E, Adobe Firefly, and other C2PA-compliant tools embed a signed manifest. `mtsb info` extracts and displays:

- **Software agent** (e.g. `gpt-image` → "ChatGPT (OpenAI)")
- **Claim generator** (e.g. `OpenAI Media Service API`)
- **Actions** (created, converted, watermarked)
- **Timestamps**, certificates, signatures, and more

### 🎯 Accurate AI Tool Detection
| Tool | Detected As |
|------|-------------|
| ChatGPT / DALL-E | `ChatGPT (OpenAI)` |
| Midjourney | `Midjourney` |
| Stable Diffusion (A1111) | `Stable Diffusion (A1111)` |
| ComfyUI | `ComfyUI` |
| Adobe Firefly | `Adobe Firefly` |
| Canva | Not AI — treated as human editing app |

### 🛠️ Data Manipulation
- **Auto Organic** — Random realistic camera profile (Canon, Nikon, Sony, Fujifilm, etc.) with matching shooting settings
- **Custom Edit** — Manually type every EXIF field: make, model, lens, ISO, aperture, shutter speed, GPS, description, artist, copyright
- **Design App** — Inject metadata mimicking Photoshop, Procreate, Clip Studio Paint, Krita, GIMP, Canva, etc.

## 🖼️ Supported Formats

| Format | Details |
|--------|---------|
| PNG | C2PA, text chunks, and EXIF |
| JPEG / JPG | Full EXIF + XMP metadata |
| WebP | Metadata support |

## 📄 License

[MIT](LICENSE)
