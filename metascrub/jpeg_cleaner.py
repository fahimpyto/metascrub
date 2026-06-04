import struct

from metascrub.detectors import AI_SOFTWARE_SIGNATURES, AI_DESCRIPTION_SIGNATURES

EXIF_HEADER = b'Exif\x00\x00'
XMP_HEADER = b'http://ns.adobe.com/xap/1.0/'


def parse_markers(data: bytes):
    markers = []
    pos = 2
    while pos + 2 <= len(data):
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos+1]
        if marker == 0x00:
            pos += 2
            continue
        if marker == 0xD9:
            markers.append((pos, marker, 0, b''))
            break
        if marker == 0xDA:
            seg_len = struct.unpack('>H', data[pos+2:pos+4])[0]
            markers.append((pos, marker, seg_len, bytearray(data[pos+2:pos+2+seg_len])))
            break
        if marker in range(0xD0, 0xD8):
            markers.append((pos, marker, 0, b''))
            pos += 2
            continue
        seg_len = struct.unpack('>H', data[pos+2:pos+4])[0]
        if seg_len < 2:
            pos += 2
            continue
        markers.append((pos, marker, seg_len, bytearray(data[pos+2:pos+2+seg_len])))
        pos += 2 + seg_len
    return markers


def _append_marker(result: bytearray, marker_byte: int, seg_data: bytearray | bytes):
    result.extend(b'\xff' + bytes([marker_byte]))
    result.extend(seg_data)


def clean_jpeg(data: bytes, organic: bool | bytes = False) -> bytes:
    if data[0:2] != b'\xff\xd8':
        raise ValueError("Not a valid JPEG file")

    markers = parse_markers(data)
    cleaned_exif_bytes = None
    has_exif = False
    result = bytearray(b'\xff\xd8')
    exif_was_removed = False

    for pos, marker, seg_len, seg_data in markers:
        if marker == 0xD9:
            result.extend(b'\xff\xd9')
            break

        if marker == 0xDA:
            _append_marker(result, marker, seg_data)
            sos_end = pos + 2 + seg_len
            result.extend(data[sos_end:])
            if organic and (cleaned_exif_bytes or exif_was_removed or not has_exif):
                if isinstance(organic, bytes):
                    exif_bytes = organic
                else:
                    width, height = _get_dimensions_from_result(result)
                    if width and height:
                        exif_bytes = cleaned_exif_bytes
                        if exif_bytes is None:
                            from metascrub.injector import make_organic_exif_blob
                            exif_bytes = make_organic_exif_blob(width, height)
                if exif_bytes is not None:
                    insert_pos = _find_insert_pos(result)
                    app1_data = struct.pack('>H', len(exif_bytes)) + exif_bytes
                    result[insert_pos:insert_pos] = b'\xff\xe1' + app1_data
            break

        if marker == 0xE1:
            payload = seg_data[2:] if len(seg_data) > 2 else b''
            if payload.startswith(XMP_HEADER):
                exif_was_removed = True
                continue
            if payload.startswith(EXIF_HEADER):
                has_exif = True
                try:
                    import piexif
                    exif_dict = piexif.load(payload)
                    modified = _clean_exif_dict(exif_dict)
                    if modified is not None:
                        cleaned_exif_bytes = piexif.dump(modified)
                        _append_marker(result, marker, struct.pack('>H', len(cleaned_exif_bytes)) + cleaned_exif_bytes)
                    else:
                        exif_was_removed = True
                except Exception:
                    _append_marker(result, marker, seg_data)
                continue
            _append_marker(result, marker, seg_data)
            continue

        if marker in (0xEB, 0xEE, 0xEF):
            payload = seg_data[2:] if len(seg_data) > 2 else b''
            lower = payload.lower()
            if (lower.startswith(XMP_HEADER) or
                b'c2pa' in lower or b'contentcredentials' in lower or
                b'creativemetadata' in lower or b'dalle' in lower):
                continue
            _append_marker(result, marker, seg_data)
            continue

        if marker == 0xED:
            payload = seg_data[2:] if len(seg_data) > 2 else b''
            if b'creativemetadata' in payload.lower():
                continue
            _append_marker(result, marker, seg_data)
            continue

        _append_marker(result, marker, seg_data)

    if organic and not has_exif and not cleaned_exif_bytes and not exif_was_removed:
        if isinstance(organic, bytes):
            exif_bytes = organic
        else:
            width, height = _get_dimensions_from_result(result)
            if width and height:
                from .injector import make_organic_exif_blob
                exif_bytes = make_organic_exif_blob(width, height)
            else:
                exif_bytes = None
        if exif_bytes is not None:
            insert_pos = _find_insert_pos(result)
            app1_data = struct.pack('>H', len(exif_bytes)) + exif_bytes
            result[insert_pos:insert_pos] = b'\xff\xe1' + app1_data

    return bytes(result)


def _clean_exif_dict(exif_dict: dict) -> dict | None:
    import piexif
    modified = False
    EXIF_POINTER = piexif.ImageIFD.ExifTag  # 0x8769
    GPS_POINTER = piexif.ImageIFD.GPSTag     # 0x8825
    EXIF_POINTERS = {EXIF_POINTER, GPS_POINTER}

    desc_tags = {
        piexif.ImageIFD.ImageDescription,
        piexif.ExifIFD.UserComment,
        piexif.ImageIFD.XPComment,
    }

    for ifd_name in ('0th', 'Exif', 'GPS', '1st'):
        ifd = exif_dict.get(ifd_name)
        if not isinstance(ifd, dict):
            continue
        tags_to_del = []
        for tag_id, value in ifd.items():
            if isinstance(value, (bytes, bytearray)):
                if isinstance(value, bytearray):
                    value = bytes(value)
                val_lower = value.decode('utf-8', errors='replace').lower()

                if tag_id in desc_tags:
                    for sig in AI_DESCRIPTION_SIGNATURES:
                        if sig in val_lower:
                            tags_to_del.append(tag_id)
                            break
                    if tag_id in tags_to_del:
                        continue

                for sig in AI_SOFTWARE_SIGNATURES:
                    if sig in val_lower and len(sig) > 2:
                        tags_to_del.append(tag_id)
                        break
        for tag_id in tags_to_del:
            del ifd[tag_id]
            modified = True

    if modified:
        ifd0 = exif_dict.get('0th', {})
        exif_ifd = exif_dict.get('Exif', {})
        gps_ifd = exif_dict.get('GPS', {})

        if EXIF_POINTER in ifd0 and not exif_ifd:
            del ifd0[EXIF_POINTER]
        if GPS_POINTER in ifd0 and not gps_ifd:
            del ifd0[GPS_POINTER]

        for ifd_name in ('0th', 'Exif', 'GPS', '1st'):
            ifd = exif_dict.get(ifd_name)
            if isinstance(ifd, dict) and {k for k in ifd if k not in EXIF_POINTERS}:
                return exif_dict
        return None

    return exif_dict


def _get_dimensions_from_result(data: bytes) -> tuple:
    pos = 2
    while pos + 8 <= len(data):
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos+1]
        if marker == 0xDA:
            break
        if marker == 0x00 or marker in range(0xD0, 0xD8):
            pos += 2
            continue
        if pos + 4 > len(data):
            break
        seg_len = struct.unpack('>H', data[pos+2:pos+4])[0]
        if seg_len < 2:
            pos += 2
            continue
        if marker in (0xC0, 0xC1, 0xC2):
            if pos + 11 <= len(data):
                height = struct.unpack('>H', data[pos+5:pos+7])[0]
                width = struct.unpack('>H', data[pos+7:pos+9])[0]
                return width, height
        pos += 2 + seg_len
    return None, None


def _find_insert_pos(data: bytes) -> int:
    pos = 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos+1]
        if marker == 0xDA:
            return pos
        if marker == 0x00 or marker in range(0xD0, 0xD8):
            pos += 2
            continue
        seg_len = struct.unpack('>H', data[pos+2:pos+4])[0]
        if seg_len < 2:
            pos += 2
            continue
        pos += 2 + seg_len
    return len(data)
