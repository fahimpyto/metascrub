import random
from datetime import datetime, timedelta


CAMERA_PROFILES = [
    {"make": "Canon", "model": "Canon EOS R5", "lens": "RF 24-70mm f/2.8L IS USM"},
    {"make": "Canon", "model": "Canon EOS R6 Mark II", "lens": "RF 50mm f/1.2L USM"},
    {"make": "Nikon", "model": "Nikon Z8", "lens": "NIKKOR Z 24-70mm f/2.8 S"},
    {"make": "Nikon", "model": "Nikon Z6 III", "lens": "NIKKOR Z 50mm f/1.8 S"},
    {"make": "SONY", "model": "ILCE-7RM5", "lens": "FE 24-70mm F2.8 GM II"},
    {"make": "SONY", "model": "ILCE-9M3", "lens": "FE 50mm F1.4 GM"},
    {"make": "FUJIFILM", "model": "X-T5", "lens": "XF 23mm F1.4 R LM WR"},
    {"make": "Panasonic", "model": "DC-S5M2", "lens": "LUMIX S 24-105mm F4 MACRO O.I.S."},
]

SHUTTER_SPEEDS = [
    (1, 4000), (1, 2000), (1, 1000), (1, 500), (1, 250),
    (1, 125), (1, 60), (1, 30), (1, 15),
]

F_STOPS = [
    (14, 10), (16, 10), (18, 10), (20, 10),
    (22, 10), (25, 10), (28, 10), (32, 10),
    (35, 10), (40, 10), (45, 10), (56, 10),
    (63, 10), (71, 10), (80, 10),
]

FOCAL_LENGTHS = [(24, 1), (28, 1), (35, 1), (50, 1), (85, 1),
                 (105, 1), (135, 1), (200, 1), (70, 1), (16, 1)]

ISO_VALUES = [100, 200, 400, 800, 1600, 3200, 6400]


def _random_date() -> str:
    start = datetime(2020, 1, 1)
    end = datetime(2025, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    random_seconds = random.randint(0, 86400)
    d = start + timedelta(days=random_days, seconds=random_seconds)
    return d.strftime("%Y:%m:%d %H:%M:%S")


def _random_date_near() -> str:
    d = datetime.now() - timedelta(
        days=random.randint(0, 1095),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )
    return d.strftime("%Y:%m:%d %H:%M:%S")


def _build_exif_dict(width: int | None = None, height: int | None = None) -> dict:
    import piexif

    camera = random.choice(CAMERA_PROFILES)
    date_str = _random_date()
    shutter = random.choice(SHUTTER_SPEEDS)
    fstop = random.choice(F_STOPS)
    focal = random.choice(FOCAL_LENGTHS)
    iso = random.choice(ISO_VALUES)

    exif_dict = {
        '0th': {},
        'Exif': {},
        'GPS': {},
        '1st': {},
        'thumbnail': None,
    }

    exif_dict['0th'][piexif.ImageIFD.Make] = camera['make'].encode()
    exif_dict['0th'][piexif.ImageIFD.Model] = camera['model'].encode()
    exif_dict['0th'][piexif.ImageIFD.Orientation] = 1
    exif_dict['0th'][piexif.ImageIFD.XResolution] = (300, 1)
    exif_dict['0th'][piexif.ImageIFD.YResolution] = (300, 1)
    exif_dict['0th'][piexif.ImageIFD.ResolutionUnit] = 2
    exif_dict['0th'][piexif.ImageIFD.DateTime] = date_str.encode()
    exif_dict['0th'][piexif.ImageIFD.Software] = b'Adobe Lightroom Classic 14.0'

    exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = date_str.encode()
    exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = date_str.encode()
    exif_dict['Exif'][piexif.ExifIFD.ExposureTime] = shutter
    exif_dict['Exif'][piexif.ExifIFD.FNumber] = fstop
    exif_dict['Exif'][piexif.ExifIFD.ISOSpeedRatings] = iso
    exif_dict['Exif'][piexif.ExifIFD.FocalLength] = focal
    exif_dict['Exif'][piexif.ExifIFD.Flash] = 0
    exif_dict['Exif'][piexif.ExifIFD.MeteringMode] = 5
    exif_dict['Exif'][piexif.ExifIFD.WhiteBalance] = 0
    exif_dict['Exif'][piexif.ExifIFD.ColorSpace] = 1
    exif_dict['Exif'][piexif.ExifIFD.ExposureProgram] = 3
    exif_dict['Exif'][piexif.ExifIFD.FocalLengthIn35mmFilm] = focal[0]
    exif_dict['Exif'][piexif.ExifIFD.SceneCaptureType] = 0
    exif_dict['Exif'][piexif.ExifIFD.ShutterSpeedValue] = shutter
    exif_dict['Exif'][piexif.ExifIFD.ApertureValue] = fstop
    exif_dict['Exif'][piexif.ExifIFD.BrightnessValue] = (0, 1)
    exif_dict['Exif'][piexif.ExifIFD.SubSecTimeOriginal] = str(random.randint(10, 99)).encode()
    exif_dict['Exif'][piexif.ExifIFD.CustomRendered] = 0
    exif_dict['Exif'][piexif.ExifIFD.ExposureMode] = 0
    exif_dict['Exif'][piexif.ExifIFD.DigitalZoomRatio] = (1, 1)
    exif_dict['Exif'][piexif.ExifIFD.GainControl] = 0
    exif_dict['Exif'][piexif.ExifIFD.Contrast] = 0
    exif_dict['Exif'][piexif.ExifIFD.Saturation] = 0
    exif_dict['Exif'][piexif.ExifIFD.Sharpness] = 0

    if width and height:
        exif_dict['Exif'][piexif.ExifIFD.PixelXDimension] = width
        exif_dict['Exif'][piexif.ExifIFD.PixelYDimension] = height

    return exif_dict


def make_organic_exif_blob(width: int | None = None, height: int | None = None) -> bytes:
    import piexif
    exif_dict = _build_exif_dict(width, height)
    return piexif.dump(exif_dict)


def make_canva_exif_blob(width: int | None = None, height: int | None = None) -> bytes:
    import piexif
    date_str = datetime.now().strftime("%Y:%m:%d %H:%M:%S")

    exif_dict = {
        '0th': {},
        'Exif': {},
        'GPS': {},
        '1st': {},
        'thumbnail': None,
    }

    exif_dict['0th'][piexif.ImageIFD.Make] = b'Canva'
    exif_dict['0th'][piexif.ImageIFD.Model] = b'Canva'
    exif_dict['0th'][piexif.ImageIFD.Software] = b'Canva'
    exif_dict['0th'][piexif.ImageIFD.Orientation] = 1
    exif_dict['0th'][piexif.ImageIFD.XResolution] = (72, 1)
    exif_dict['0th'][piexif.ImageIFD.YResolution] = (72, 1)
    exif_dict['0th'][piexif.ImageIFD.ResolutionUnit] = 2
    exif_dict['0th'][piexif.ImageIFD.DateTime] = date_str.encode()

    exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = date_str.encode()
    exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = date_str.encode()
    exif_dict['Exif'][piexif.ExifIFD.ColorSpace] = 1
    exif_dict['Exif'][piexif.ExifIFD.PixelXDimension] = width or 0
    exif_dict['Exif'][piexif.ExifIFD.PixelYDimension] = height or 0

    return piexif.dump(exif_dict)


def inject_canva_metadata(file_path: "Path", fmt: str | None = None) -> "Path":
    from metascrub.cleaner import clean_file, get_format

    fmt = fmt or get_format(file_path)
    if not fmt:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

    if fmt == 'png':
        _inject_canva_png(file_path)
    else:
        w, h = _get_pillow_dims(file_path)
        blob = make_canva_exif_blob(w, h)
        clean_file(file_path, exif_blob=blob, in_place=True)

    return file_path


def _inject_canva_png(file_path: "Path"):
    from metascrub.png_cleaner import read_chunks, rebuild_png, make_chunk
    data = file_path.read_bytes()
    chunks = read_chunks(data)

    new_chunks = []
    has_software = False
    insert_idx = len(chunks)

    for i, (ct, cd, crc) in enumerate(chunks):
        if ct == b'IDAT' and insert_idx == len(chunks):
            insert_idx = i
        if ct in (b'tEXt', b'iTXt', b'zTXt'):
            null_pos = cd.find(b'\0')
            if null_pos > 0:
                kw = cd[:null_pos].decode('latin-1', errors='replace').lower()
                if kw == 'software':
                    has_software = True
                    continue
        if ct == b'eXIf':
            continue
        new_chunks.append((ct, cd, crc))

    sw_chunk = make_chunk(b'tEXt', b'Software\x00Canva')
    new_chunks.insert(insert_idx, sw_chunk)
    insert_idx += 1

    w, h = _get_png_dims(new_chunks)
    exif_blob = make_canva_exif_blob(w, h)
    if exif_blob.startswith(b'Exif\x00\x00'):
        exif_blob = exif_blob[6:]
    exif_chunk = make_chunk(b'eXIf', exif_blob)
    new_chunks.insert(insert_idx, exif_chunk)

    file_path.write_bytes(rebuild_png(new_chunks))


def _get_png_dims(chunks: list) -> tuple:
    for ct, cd, _ in chunks:
        if ct == b'IHDR' and len(cd) >= 8:
            import struct
            w = struct.unpack('>I', cd[0:4])[0]
            h = struct.unpack('>I', cd[4:8])[0]
            return w, h
    return None, None


def _get_pillow_dims(file_path: "Path") -> tuple:
    try:
        from PIL import Image
        img = Image.open(file_path)
        return img.size
    except Exception:
        return None, None


DESIGN_APP_PROFILES = [
    {"software": "Adobe Photoshop 2026", "make": "Adobe Inc.", "model": "Photoshop"},
    {"software": "Adobe Illustrator 2026", "make": "Adobe Inc.", "model": "Illustrator"},
    {"software": "Procreate", "make": "Savage Interactive", "model": "Procreate"},
    {"software": "Clip Studio Paint 3.0", "make": "Celsys", "model": "Clip Studio Paint"},
    {"software": "Affinity Designer 2", "make": "Serif", "model": "Affinity Designer 2"},
    {"software": "Krita 5.2", "make": "Krita Foundation", "model": "Krita"},
    {"software": "GIMP 2.99", "make": "GIMP", "model": "GIMP"},
    {"software": "CorelDRAW 2024", "make": "Corel Corporation", "model": "CorelDRAW"},
    {"software": "Canva", "make": "Canva", "model": "Canva"},
]


def make_design_exif_blob(
    width: int | None = None,
    height: int | None = None,
) -> bytes:
    import piexif
    import random

    profile = random.choice(DESIGN_APP_PROFILES)
    date_str = _random_date_near()

    exif_dict = {
        '0th': {},
        'Exif': {},
        'GPS': {},
        '1st': {},
        'thumbnail': None,
    }

    exif_dict['0th'][piexif.ImageIFD.Make] = profile['make'].encode()
    exif_dict['0th'][piexif.ImageIFD.Model] = profile['model'].encode()
    exif_dict['0th'][piexif.ImageIFD.Software] = profile['software'].encode()
    exif_dict['0th'][piexif.ImageIFD.Orientation] = 1
    exif_dict['0th'][piexif.ImageIFD.XResolution] = (300, 1)
    exif_dict['0th'][piexif.ImageIFD.YResolution] = (300, 1)
    exif_dict['0th'][piexif.ImageIFD.ResolutionUnit] = 2
    exif_dict['0th'][piexif.ImageIFD.DateTime] = date_str.encode()

    exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = date_str.encode()
    exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = date_str.encode()
    exif_dict['Exif'][piexif.ExifIFD.ColorSpace] = 1

    if width and height:
        exif_dict['Exif'][piexif.ExifIFD.PixelXDimension] = width
        exif_dict['Exif'][piexif.ExifIFD.PixelYDimension] = height

    return piexif.dump(exif_dict)


def make_custom_exif_blob(
    width: int | None = None,
    height: int | None = None,
    make: str | None = None,
    model: str | None = None,
    lens: str | None = None,
    software: str | None = None,
    date_str: str | None = None,
    iso: int | None = None,
    fnumber: tuple[int, int] | None = None,
    shutter: tuple[int, int] | None = None,
    focal: tuple[int, int] | None = None,
    description: str | None = None,
    artist: str | None = None,
    copyright_s: str | None = None,
    gps_lat: tuple[float, str] | None = None,
    gps_lon: tuple[float, str] | None = None,
    gps_alt: float | None = None,
) -> bytes:
    import piexif

    camera = random.choice(CAMERA_PROFILES)
    date_str = date_str or _random_date_near()
    shutter = shutter or random.choice(SHUTTER_SPEEDS)
    fstop = fnumber or random.choice(F_STOPS)
    focal_len = focal or random.choice(FOCAL_LENGTHS)
    iso_val = iso or random.choice(ISO_VALUES)
    cam_make = (make or camera["make"]).encode()
    cam_model = (model or camera["model"]).encode()
    cam_lens = (lens or camera["lens"]).encode()

    exif_dict = {
        '0th': {},
        'Exif': {},
        'GPS': {},
        '1st': {},
        'thumbnail': None,
    }

    exif_dict['0th'][piexif.ImageIFD.Make] = cam_make
    exif_dict['0th'][piexif.ImageIFD.Model] = cam_model
    exif_dict['0th'][piexif.ImageIFD.Orientation] = 1
    exif_dict['0th'][piexif.ImageIFD.XResolution] = (300, 1)
    exif_dict['0th'][piexif.ImageIFD.YResolution] = (300, 1)
    exif_dict['0th'][piexif.ImageIFD.ResolutionUnit] = 2
    exif_dict['0th'][piexif.ImageIFD.DateTime] = date_str.encode()
    exif_dict['0th'][piexif.ImageIFD.Software] = (software or 'Adobe Lightroom Classic 14.0').encode()

    if description:
        exif_dict['0th'][piexif.ImageIFD.ImageDescription] = description.encode()
    if artist:
        exif_dict['0th'][piexif.ImageIFD.Artist] = artist.encode()
    if copyright_s:
        exif_dict['0th'][piexif.ImageIFD.Copyright] = copyright_s.encode()

    exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = date_str.encode()
    exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = date_str.encode()
    exif_dict['Exif'][piexif.ExifIFD.ExposureTime] = shutter
    exif_dict['Exif'][piexif.ExifIFD.FNumber] = fstop
    exif_dict['Exif'][piexif.ExifIFD.ISOSpeedRatings] = iso_val
    exif_dict['Exif'][piexif.ExifIFD.FocalLength] = focal_len
    exif_dict['Exif'][piexif.ExifIFD.Flash] = 0
    exif_dict['Exif'][piexif.ExifIFD.MeteringMode] = 5
    exif_dict['Exif'][piexif.ExifIFD.WhiteBalance] = 0
    exif_dict['Exif'][piexif.ExifIFD.ColorSpace] = 1
    exif_dict['Exif'][piexif.ExifIFD.ExposureProgram] = 3
    exif_dict['Exif'][piexif.ExifIFD.FocalLengthIn35mmFilm] = focal_len[0]
    exif_dict['Exif'][piexif.ExifIFD.SceneCaptureType] = 0
    exif_dict['Exif'][piexif.ExifIFD.ShutterSpeedValue] = shutter
    exif_dict['Exif'][piexif.ExifIFD.ApertureValue] = fstop
    exif_dict['Exif'][piexif.ExifIFD.BrightnessValue] = (0, 1)
    exif_dict['Exif'][piexif.ExifIFD.SubSecTimeOriginal] = str(random.randint(10, 99)).encode()
    exif_dict['Exif'][piexif.ExifIFD.CustomRendered] = 0
    exif_dict['Exif'][piexif.ExifIFD.ExposureMode] = 0
    exif_dict['Exif'][piexif.ExifIFD.DigitalZoomRatio] = (1, 1)
    exif_dict['Exif'][piexif.ExifIFD.GainControl] = 0
    exif_dict['Exif'][piexif.ExifIFD.Contrast] = 0
    exif_dict['Exif'][piexif.ExifIFD.Saturation] = 0
    exif_dict['Exif'][piexif.ExifIFD.Sharpness] = 0

    if width and height:
        exif_dict['Exif'][piexif.ExifIFD.PixelXDimension] = width
        exif_dict['Exif'][piexif.ExifIFD.PixelYDimension] = height

    if gps_lat is not None:
        _set_gps_coord(exif_dict, piexif.GPSIFD.GPSLatitude, piexif.GPSIFD.GPSLatitudeRef, gps_lat)
    if gps_lon is not None:
        _set_gps_coord(exif_dict, piexif.GPSIFD.GPSLongitude, piexif.GPSIFD.GPSLongitudeRef, gps_lon)
    if gps_alt is not None:
        alt_ref = 0 if gps_alt >= 0 else 1
        exif_dict['GPS'][piexif.GPSIFD.GPSAltitude] = (int(abs(gps_alt) * 100), 100)
        exif_dict['GPS'][piexif.GPSIFD.GPSAltitudeRef] = alt_ref

    return piexif.dump(exif_dict)


def _set_gps_coord(exif_dict, coord_tag, ref_tag, coord):
    value, ref = coord
    deg = int(abs(value))
    min_frac = (abs(value) - deg) * 60
    mn = int(min_frac)
    sec = int((min_frac - mn) * 60 * 100)
    exif_dict['GPS'][coord_tag] = ((deg, 1), (mn, 1), (sec, 100))
    exif_dict['GPS'][ref_tag] = ref.encode() if isinstance(ref, str) else ref
