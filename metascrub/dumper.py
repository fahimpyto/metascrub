import hashlib
import struct
from datetime import datetime
from pathlib import Path

from metascrub.detectors import detect_ai_image
from metascrub.cleaner import get_format


def dump_image(path: Path) -> dict:
    fmt = get_format(path)
    if not fmt:
        raise ValueError(f"Unsupported format: {path.suffix}")

    data = path.read_bytes()
    stat = path.stat()

    result = {
        "file": {
            "path": str(path.resolve()),
            "name": path.name,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "sha256": hashlib.sha256(data).hexdigest(),
            "format": fmt,
        },
        "ai": detect_ai_image(data, fmt),
        "structure": [],
    }

    if fmt == "png":
        _dump_png(data, result)
    elif fmt == "jpeg":
        _dump_jpeg(data, result)
    elif fmt == "webp":
        _dump_webp(data, result)

    return result


# ─── PNG ──────────────────────────────────────────────────────────────

PNG_CHUNK_DECODERS = {}


def _register(t: bytes):
    def wrap(fn):
        PNG_CHUNK_DECODERS[t] = fn
        return fn
    return wrap


def _dump_png(data: bytes, result: dict):
    from metascrub.png_cleaner import read_chunks
    from metascrub.c2pa import parse_c2pa, format_c2pa_summary
    chunks = read_chunks(data)
    result["structure"] = []
    text_chunks = []
    raw_exif = None
    c2pa_data = {}

    for i, (ct, cd, crc) in enumerate(chunks):
        entry = {
            "index": i,
            "type": ct.decode("latin-1", errors="replace"),
            "length": len(cd),
            "crc": crc.hex(),
        }
        fn = PNG_CHUNK_DECODERS.get(ct)
        decoded = fn(cd) if fn else None
        if decoded:
            entry["decoded"] = decoded

        if ct in (b'tEXt', b'iTXt', b'zTXt') and cd:
            null_pos = cd.find(b'\0')
            if null_pos > 0:
                kw = cd[:null_pos].decode("latin-1", errors="replace")
                val = cd[null_pos+1:].decode("latin-1", errors="replace")
                text_chunks.append({"keyword": kw, "value": val})
                entry["key"] = kw
                entry["value"] = val[:200]

        if ct == b'eXIf':
            raw_exif = cd[6:] if cd.startswith(b'Exif\x00\x00') else cd

        if ct == b'caBX' and len(cd) > 0:
            try:
                parsed = parse_c2pa(cd)
                if parsed:
                    c2pa_data = parsed
            except Exception:
                pass

        result["structure"].append(entry)

    result["text_chunks"] = text_chunks
    if c2pa_data:
        result["c2pa"] = c2pa_data
    _parse_raw_exif(raw_exif, result)


@_register(b'IHDR')
def _decode_ihdr(cd):
    w, h = struct.unpack('>II', cd[0:8])
    bit_depth = cd[8]
    color_type = cd[9]
    color_names = {0: "Grayscale", 2: "RGB", 3: "Indexed", 4: "Grayscale+Alpha", 6: "RGBA"}
    return {
        "width": w, "height": h, "bit_depth": bit_depth,
        "color_type": color_names.get(color_type, f"Unknown ({color_type})"),
    }


@_register(b'gAMA')
def _decode_gama(cd):
    gamma = struct.unpack('>I', cd)[0] / 100000
    return {"gamma": round(gamma, 4)}


@_register(b'sRGB')
def _decode_srgb(cd):
    intents = {0: "Perceptual", 1: "Relative Colorimetric", 2: "Saturation", 3: "Absolute Colorimetric"}
    return {"rendering_intent": intents.get(cd[0], f"Unknown ({cd[0]})")}


@_register(b'pHYs')
def _decode_phys(cd):
    ppu_x, ppu_y = struct.unpack('>II', cd[0:8])
    unit = "meters" if cd[8] == 1 else "unknown"
    return {"pixels_per_unit_x": ppu_x, "pixels_per_unit_y": ppu_y, "unit": unit}


@_register(b'tIME')
def _decode_time(cd):
    y, m, d, h, mn, s = struct.unpack('>HBBBBB', cd)
    return {"timestamp": f"{y:04d}-{m:02d}-{d:02d} {h:02d}:{mn:02d}:{s:02d}"}


@_register(b'PLTE')
def _decode_plte(cd):
    return {"color_count": len(cd) // 3}


@_register(b'bKGD')
def _decode_bkgd(cd):
    return {"hex": cd.hex()}


@_register(b'caBX')
def _decode_cabx(cd):
    return {"c2pa": "C2PA content credentials", "size": len(cd)}


@_register(b'caMs')
def _decode_cams(cd):
    return {"c2pa": "C2PA manifest store", "size": len(cd)}


@_register(b'caSt')
def _decode_cast(cd):
    return {"c2pa": "C2PA manifest store (thumbnail)", "size": len(cd)}


# ─── JPEG ─────────────────────────────────────────────────────────────

MARKER_NAMES = {
    0xC0: "SOF0 (Baseline)", 0xC1: "SOF1 (Extended)", 0xC2: "SOF2 (Progressive)",
    0xC4: "DHT (Huffman Table)", 0xDB: "DQT (Quantization Table)",
    0xDD: "DRI (Restart Interval)", 0xDA: "SOS (Start of Scan)",
    0xD0: "RST0", 0xD1: "RST1", 0xD2: "RST2", 0xD3: "RST3",
    0xD4: "RST4", 0xD5: "RST5", 0xD6: "RST6", 0xD7: "RST7",
    0xD8: "SOI (Start of Image)", 0xD9: "EOI (End of Image)",
    0xE0: "APP0 (JFIF)", 0xE1: "APP1 (EXIF / XMP)",
    0xE2: "APP2 (ICC Profile)", 0xED: "APP13 (IPTC / Photoshop)",
    0xEB: "APP11 (C2PA)", 0xEE: "APP14 (Adobe / C2PA)",
    0xEF: "APP15 (C2PA)", 0xFE: "COM (Comment)",
}


def _dump_jpeg(data: bytes, result: dict):
    from metascrub.jpeg_cleaner import parse_markers
    markers = parse_markers(data)
    result["structure"] = []
    raw_exif = None
    jfif_info = None
    xmp_text = None
    icc_data = None
    comments = []

    for pos, marker, seg_len, seg_data in markers:
        name = MARKER_NAMES.get(marker, f"0x{marker:02X}")
        entry = {
            "offset": pos,
            "marker": f"0xFF{marker:02X}",
            "name": name,
            "length": seg_len,
        }

        if marker == 0xE1:
            if seg_data.startswith(b'Exif\x00\x00'):
                raw_exif = seg_data
                entry["content"] = f"EXIF ({len(seg_data)} bytes)"
            elif seg_data.startswith(b'http://ns.adobe.com/xap/1.0/'):
                try:
                    xmp_text = seg_data.decode("utf-8", errors="replace")
                    entry["content"] = "XMP metadata"
                except Exception:
                    entry["content"] = "XMP (undecodable)"

        elif marker == 0xE0 and seg_data.startswith(b'JFIF\x00'):
            try:
                ver_major, ver_minor = seg_data[5], seg_data[6]
                density = seg_data[7]
                density_units = {0: "No units", 1: "Dots per inch", 2: "Dots per cm"}
                x_dens = struct.unpack('>H', seg_data[8:10])[0]
                y_dens = struct.unpack('>H', seg_data[10:12])[0]
                thumb_w, thumb_h = seg_data[12], seg_data[13] if len(seg_data) > 12 else 0
                jfif_info = {
                    "version": f"{ver_major}.{ver_minor}",
                    "density_unit": density_units.get(density, str(density)),
                    "x_density": x_dens, "y_density": y_dens,
                    "thumbnail": f"{thumb_w}x{thumb_h}" if thumb_w and thumb_h else "none",
                }
                entry["content"] = jfif_info
            except Exception:
                pass

        elif marker == 0xFE:
            try:
                text = seg_data.decode("utf-8", errors="replace").strip()
                if text:
                    comments.append(text)
                    entry["content"] = text[:200]
            except Exception:
                pass

        elif marker == 0xE2 and seg_data.startswith(b'ICC_PROFILE\x00'):
            icc_data = seg_data
            entry["content"] = f"ICC profile ({len(seg_data)} bytes)"

        elif marker in (0xC0, 0xC1, 0xC2) and len(seg_data) >= 6:
            precision = seg_data[0]
            height = struct.unpack('>H', seg_data[1:3])[0]
            width = struct.unpack('>H', seg_data[3:5])[0]
            components = seg_data[5]
            entry["content"] = {
                "precision": precision, "width": width,
                "height": height, "components": components,
            }

        elif marker == 0xDB and seg_data:
            tables = []
            pos_in = 0
            while pos_in + 1 < len(seg_data):
                info = seg_data[pos_in]
                table_id = info & 0x0F
                precision = (info >> 4) & 0x0F
                table_size = 64 if precision == 0 else 128
                if pos_in + 1 + table_size <= len(seg_data):
                    tables.append({"id": table_id, "precision": f"{precision}-byte"})
                    pos_in += 1 + table_size
                else:
                    break
            entry["content"] = f"{len(tables)} quantization table(s)"

        elif marker in (0xEB, 0xEE, 0xEF):
            entry["content"] = f"C2PA content ({seg_len} bytes)"

        result["structure"].append(entry)

    result["jfif"] = jfif_info
    result["xmp"] = xmp_text[:5000] if xmp_text else None
    result["icc_profile"] = f"{len(icc_data)} bytes" if icc_data else None
    result["comments"] = comments
    _parse_raw_exif(raw_exif, result)


# ─── WebP ─────────────────────────────────────────────────────────────

CHUNK_NAMES = {
    b'VP8 ': "VP8 (Lossy)", b'VP8L': "VP8L (Lossless)", b'VP8X': "VP8X (Extended)",
    b'EXIF': "EXIF metadata", b'XMP ': "XMP metadata",
    b'ICCP': "ICC profile", b'ALPH': "Alpha", b'ANIM': "Animation",
    b'ANMF': "Animation frame",
}


def _dump_webp(data: bytes, result: dict):
    if len(data) < 12:
        result["structure"] = [{"error": "File too small"}]
        return

    file_size = struct.unpack('<I', data[4:8])[0] + 8
    result["structure"] = []
    raw_exif = None
    xmp_text = None

    pos = 12
    while pos + 8 <= file_size:
        chunk_id = data[pos:pos+4]
        chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
        chunk_data = data[pos+8:pos+8+chunk_size]

        name = CHUNK_NAMES.get(chunk_id, chunk_id.decode("latin-1", errors="replace"))
        entry = {
            "offset": pos,
            "chunk_type": chunk_id.decode("latin-1", errors="replace"),
            "name": name,
            "length": chunk_size,
        }

        if chunk_id == b'VP8X' and len(chunk_data) >= 10:
            flags = chunk_data[0]
            features = []
            if flags & 0x01: features.append("ICC")
            if flags & 0x02: features.append("Animation")
            if flags & 0x04: features.append("EXIF metadata")
            if flags & 0x08: features.append("XMP metadata")
            if flags & 0x10: features.append("Alpha")
            w = struct.unpack('<I', chunk_data[4:7] + b'\x00')[0] + 1
            h = struct.unpack('<I', chunk_data[7:10] + b'\x00')[0] + 1
            entry["content"] = {"width": w, "height": h, "features": features}

        elif chunk_id == b'EXIF':
            raw_exif = chunk_data[6:] if chunk_data.startswith(b'Exif\x00\x00') else chunk_data
            entry["content"] = f"EXIF ({chunk_size} bytes)"

        elif chunk_id == b'XMP ':
            try:
                xmp_text = chunk_data.decode("utf-8", errors="replace")
                entry["content"] = "XMP metadata"
            except Exception:
                entry["content"] = "XMP (undecodable)"

        elif chunk_id == b'ICCP':
            entry["content"] = f"ICC profile ({chunk_size} bytes)"

        elif chunk_id == b'ANIM':
            bg_color = struct.unpack('<I', chunk_data[0:4])[0] if len(chunk_data) >= 4 else 0
            loops = struct.unpack('<H', chunk_data[4:6])[0] if len(chunk_data) >= 6 else 0
            entry["content"] = {"background_color": f"#{bg_color:06X}", "loop_count": loops}

        result["structure"].append(entry)

        pos += 8 + chunk_size
        if chunk_size % 2:
            pos += 1

    result["xmp"] = xmp_text[:5000] if xmp_text else None
    _parse_raw_exif(raw_exif, result)


# ─── EXIF ─────────────────────────────────────────────────────────────

EXIF_IFD_NAMES = {
    "0th": "Main Image IFD",
    "Exif": "EXIF Sub-IFD",
    "GPS": "GPS Sub-IFD",
    "1st": "Thumbnail IFD",
}


def _parse_raw_exif(raw_exif: bytes | None, result: dict):
    if not raw_exif:
        return

    try:
        import piexif
        exif_dict = piexif.load(raw_exif)
    except Exception:
        return

    exif_data = {}
    for ifd_name in ("0th", "Exif", "GPS", "1st"):
        ifd = exif_dict.get(ifd_name, {})
        if not ifd:
            continue
        tags = {}
        for tag_id, value in ifd.items():
            name = piexif.TAGS.get(ifd_name, {}).get(tag_id, {}).get("name", f"0x{tag_id:04X}")
            tags[name] = _fmt_exif_value(value)
        if tags:
            exif_data[ifd_name] = {"label": EXIF_IFD_NAMES.get(ifd_name, ifd_name), "tags": tags}

    thumb = exif_dict.get("thumbnail")
    if thumb:
        exif_data["thumbnail"] = f"{len(thumb)} bytes"

    if exif_data:
        result["exif"] = exif_data

    camera = _extract_camera(exif_dict)
    if camera:
        result["camera"] = camera

    gps = _extract_gps(exif_dict)
    if gps:
        result["gps"] = gps

    shooting = _extract_shooting(exif_dict)
    if shooting:
        result["shooting"] = shooting

    dates = _extract_dates(exif_dict)
    if dates:
        result["dates"] = dates

    copyright_info = _extract_copyright(exif_dict)
    if copyright_info:
        result["copyright"] = copyright_info


def _fmt_exif_value(value):
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace").strip()
        except Exception:
            return value.hex()
    if isinstance(value, tuple) and len(value) == 2:
        if value[1] != 0:
            return round(value[0] / value[1], 4)
        return str(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _extract_camera(exif_dict: dict) -> dict | None:
    camera = {}
    import piexif
    ifd0 = exif_dict.get("0th", {})
    for tag_id, name in [(piexif.ImageIFD.Make, "make"),
                          (piexif.ImageIFD.Model, "model"),
                          (piexif.ImageIFD.Software, "software"),
                          (piexif.ImageIFD.Artist, "artist")]:
        val = ifd0.get(tag_id)
        if val:
            camera[name] = _fmt_exif_value(val)

    exif = exif_dict.get("Exif", {})
    for tag_id, name in [(piexif.ExifIFD.LensModel, "lens_model"),
                          (piexif.ExifIFD.LensSpecification, "lens_spec"),
                          (piexif.ExifIFD.BodySerialNumber, "body_serial"),
                          (piexif.ExifIFD.LensSerialNumber, "lens_serial")]:
        val = exif.get(tag_id)
        if val:
            camera[name] = _fmt_exif_value(val)
    return camera if camera else None


def _extract_gps(exif_dict: dict) -> dict | None:
    gps_ifd = exif_dict.get("GPS", {})
    if not gps_ifd:
        return None
    import piexif
    gps = {}
    lat_raw = gps_ifd.get(piexif.GPSIFD.GPSLatitude)
    lat_ref = gps_ifd.get(piexif.GPSIFD.GPSLatitudeRef)
    lon_raw = gps_ifd.get(piexif.GPSIFD.GPSLongitude)
    lon_ref = gps_ifd.get(piexif.GPSIFD.GPSLongitudeRef)
    alt = gps_ifd.get(piexif.GPSIFD.GPSAltitude)
    alt_ref = gps_ifd.get(piexif.GPSIFD.GPSAltitudeRef)

    if lat_raw and lat_ref:
        try:
            d, m, s = [_fmt_exif_value(v) for v in lat_raw]
            lat = d + m / 60 + s / 3600
            if lat_ref in (b'S', b's'):
                lat = -lat
            gps["latitude"] = round(lat, 6)
            gps["latitude_ref"] = lat_ref.decode() if isinstance(lat_ref, bytes) else str(lat_ref)
        except Exception:
            pass

    if lon_raw and lon_ref:
        try:
            d, m, s = [_fmt_exif_value(v) for v in lon_raw]
            lon = d + m / 60 + s / 3600
            if lon_ref in (b'W', b'w'):
                lon = -lon
            gps["longitude"] = round(lon, 6)
            gps["longitude_ref"] = lon_ref.decode() if isinstance(lon_ref, bytes) else str(lon_ref)
        except Exception:
            pass

    if alt is not None:
        alt_val = _fmt_exif_value(alt)
        if alt_ref is not None:
            gps["altitude"] = f"{alt_val}m" if not alt_ref else f"-{alt_val}m"
        else:
            gps["altitude"] = f"{alt_val}m"

    for tag_id, name in [(piexif.GPSIFD.GPSVersionID, "gps_version"),
                          (piexif.GPSIFD.GPSTimeStamp, "gps_timestamp"),
                          (piexif.GPSIFD.GPSDateStamp, "gps_date"),
                          (piexif.GPSIFD.GPSProcessingMethod, "processing_method"),
                          (piexif.GPSIFD.GPSImgDirection, "image_direction"),
                          (piexif.GPSIFD.GPSImgDirectionRef, "image_direction_ref")]:
        val = gps_ifd.get(tag_id)
        if val:
            gps[name] = _fmt_exif_value(val)

    return gps if gps else None


def _extract_shooting(exif_dict: dict) -> dict | None:
    exif = exif_dict.get("Exif", {})
    if not exif:
        return None
    import piexif
    shooting = {}
    for tag_id, name in [(piexif.ExifIFD.ISOSpeedRatings, "iso"),
                          (piexif.ExifIFD.FNumber, "f_number"),
                          (piexif.ExifIFD.ExposureTime, "exposure_time"),
                          (piexif.ExifIFD.FocalLength, "focal_length"),
                          (piexif.ExifIFD.Flash, "flash"),
                          (piexif.ExifIFD.MeteringMode, "metering_mode"),
                          (piexif.ExifIFD.ExposureProgram, "exposure_program"),
                          (piexif.ExifIFD.WhiteBalance, "white_balance"),
                          (piexif.ExifIFD.FocalLengthIn35mmFilm, "focal_length_35mm"),
                          (piexif.ExifIFD.DigitalZoomRatio, "digital_zoom_ratio"),
                          (piexif.ExifIFD.Contrast, "contrast"),
                          (piexif.ExifIFD.Saturation, "saturation"),
                          (piexif.ExifIFD.Sharpness, "sharpness"),
                          (piexif.ExifIFD.ShutterSpeedValue, "shutter_speed_value"),
                          (piexif.ExifIFD.ApertureValue, "aperture_value"),
                          (piexif.ExifIFD.BrightnessValue, "brightness_value"),
                          (piexif.ExifIFD.ExposureBiasValue, "exposure_bias"),
                          (piexif.ExifIFD.ColorSpace, "color_space"),
                          (piexif.ExifIFD.SceneCaptureType, "scene_capture_type"),
                          (piexif.ExifIFD.CustomRendered, "custom_rendered"),
                          (piexif.ExifIFD.ExposureMode, "exposure_mode"),
                          (piexif.ExifIFD.SensingMethod, "sensing_method"),
                          (piexif.ExifIFD.FileSource, "file_source"),
                          (piexif.ExifIFD.SceneType, "scene_type")]:
        val = exif.get(tag_id)
        if val is not None:
            shooting[name] = _fmt_exif_value(val)

    flash = exif.get(piexif.ExifIFD.Flash)
    if flash is not None:
        flash_modes = {0: "No flash", 1: "Fired", 5: "Fired (return light detected)",
                       7: "Fired (return light not detected)", 8: "On", 16: "Off",
                       24: "Auto (did not fire)", 25: "Auto (fired)",
                       29: "Auto (fired, return light detected)",
                       31: "Auto (fired, return light not detected)",
                       32: "No flash function", 65: "Fired (red-eye mode)",
                       69: "Fired (red-eye, return light)",
                       71: "Fired (red-eye, no return)",
                       73: "Fired (red-eye, compulsory)"}
        shooting["flash"] = flash_modes.get(flash, str(flash))

    return shooting if shooting else None


def _extract_dates(exif_dict: dict) -> dict | None:
    import piexif
    dates = {}
    ifd0 = exif_dict.get("0th", {})
    dt = ifd0.get(piexif.ImageIFD.DateTime)
    if dt:
        dates["modified"] = _fmt_exif_value(dt)
    exif = exif_dict.get("Exif", {})
    for tag_id, name in [(piexif.ExifIFD.DateTimeOriginal, "original"),
                          (piexif.ExifIFD.DateTimeDigitized, "digitized"),
                          (piexif.ExifIFD.SubSecTimeOriginal, "subsec_original"),
                          (piexif.ExifIFD.SubSecTimeDigitized, "subsec_digitized")]:
        val = exif.get(tag_id)
        if val:
            dates[name] = _fmt_exif_value(val)
    return dates if dates else None


def _extract_copyright(exif_dict: dict) -> dict | None:
    import piexif
    info = {}
    ifd0 = exif_dict.get("0th", {})
    for tag_id, name in [(piexif.ImageIFD.Copyright, "copyright"),
                          (piexif.ImageIFD.ImageDescription, "image_description"),
                          (piexif.ImageIFD.XPComment, "xp_comment")]:
        val = ifd0.get(tag_id)
        if val:
            info[name] = _fmt_exif_value(val)
    exif = exif_dict.get("Exif", {})
    for tag_id, name in [(piexif.ExifIFD.UserComment, "user_comment")]:
        val = exif.get(tag_id)
        if val:
            info[name] = _fmt_exif_value(val)
    return info if info else None
