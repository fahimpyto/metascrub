import struct


def clean_webp(data: bytes, organic: bool | bytes = False) -> bytes:
    if not data.startswith(b'RIFF') or data[8:12] != b'WEBP':
        raise ValueError("Not a valid WebP file")

    file_size = struct.unpack('<I', data[4:8])[0] + 8
    pos = 12

    chunks = []
    vp8x_found = False
    vp8x_data = None

    while pos + 8 <= file_size:
        chunk_id = data[pos:pos+4]
        chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
        chunk_data = data[pos+8:pos+8+chunk_size]
        chunks.append((chunk_id, chunk_size, chunk_data))

        if chunk_id == b'VP8X':
            vp8x_found = True
            vp8x_data = bytearray(chunk_data)

        pos += 8 + chunk_size
        if chunk_size % 2:
            pos += 1

    clean_chunks = []
    for chunk_id, chunk_size, chunk_data in chunks:
        if chunk_id == b'EXIF':
            continue
        if chunk_id == b'XMP ':
            continue
        clean_chunks.append((chunk_id, chunk_size, chunk_data))

    if vp8x_found and vp8x_data is not None:
        flags = vp8x_data[0]
        has_exif = bool(flags & 0x20)
        has_xmp = bool(flags & 0x40)
        if has_exif or has_xmp:
            vp8x_data[0] = flags & ~0x20 & ~0x40
            for i, (cid, cs, cd) in enumerate(clean_chunks):
                if cid == b'VP8X':
                    clean_chunks[i] = (cid, cs, bytes(vp8x_data))
                    break

        if organic:
            if isinstance(organic, bytes):
                exif_data = organic
            else:
                from metascrub.injector import make_organic_exif_blob
                w = struct.unpack('<I', vp8x_data[4:7] + b'\x00')[0] + 1
                h = struct.unpack('<I', vp8x_data[7:10] + b'\x00')[0] + 1
                exif_data = make_organic_exif_blob(w, h)
            clean_chunks.append((b'EXIF', len(exif_data), exif_data))
            vp8x_data[0] |= 0x20
            for i, (cid, cs, cd) in enumerate(clean_chunks):
                if cid == b'VP8X':
                    clean_chunks[i] = (cid, cs, bytes(vp8x_data))
                    break

    result = bytearray(b'RIFF')
    result.extend(b'\x00\x00\x00\x00')
    result.extend(b'WEBP')
    for chunk_id, chunk_size, chunk_data in clean_chunks:
        result.extend(chunk_id)
        result.extend(struct.pack('<I', chunk_size))
        result.extend(chunk_data)
        if chunk_size % 2:
            result.extend(b'\x00')

    riff_size = len(result) - 8
    result[4:8] = struct.pack('<I', riff_size)
    return bytes(result)
