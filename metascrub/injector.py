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
