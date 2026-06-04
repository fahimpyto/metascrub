import struct
import zlib

from metascrub.detectors import AI_TEXT_CHUNK_KEYS, AI_CHUNK_TYPES, PNG_SIGNATURE


def read_chunks(data: bytes):
    chunks = []
    pos = 8
    while pos + 12 <= len(data):
        length = struct.unpack('>I', data[pos:pos+4])[0]
        chunk_type = data[pos+4:pos+8]
        chunk_data = data[pos+8:pos+8+length]
        crc = data[pos+8+length:pos+12+length]
        chunks.append((chunk_type, chunk_data, crc))
        pos += 12 + length
    return chunks


def rebuild_png(chunks):
    data = bytearray(PNG_SIGNATURE)
    for chunk_type, chunk_data, crc in chunks:
        data.extend(struct.pack('>I', len(chunk_data)))
        data.extend(chunk_type)
        data.extend(chunk_data)
        data.extend(crc)
    return bytes(data)


def make_chunk(chunk_type: bytes, chunk_data: bytes):
    crc = struct.pack('>I', zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF)
    return (chunk_type, chunk_data, crc)


def is_ai_text_chunk(chunk_type: bytes, chunk_data: bytes) -> bool:
    if chunk_type not in (b'tEXt', b'iTXt', b'zTXt'):
        return False
    if not chunk_data:
        return False
    null_pos = chunk_data.find(b'\0')
    if null_pos <= 0:
        return False
    keyword = chunk_data[:null_pos].decode('latin-1', errors='replace').lower()
    return keyword in AI_TEXT_CHUNK_KEYS


def is_ai_chunk(chunk_type: bytes) -> bool:
    return chunk_type in AI_CHUNK_TYPES


def clean_png(data: bytes, organic: bool = False) -> bytes:
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("Not a valid PNG file")

    chunks = read_chunks(data)
    clean_chunks = []
    exif_replaced = False

    for chunk_type, chunk_data, crc in chunks:
        if chunk_type in (b'IHDR', b'PLTE', b'IDAT', b'IEND'):
            clean_chunks.append((chunk_type, chunk_data, crc))
            continue

        if is_ai_chunk(chunk_type):
            continue

        if is_ai_text_chunk(chunk_type, chunk_data):
            continue

        if chunk_type == b'eXIf':
            if organic:
                exif_replaced = True
            continue

        clean_chunks.append((chunk_type, chunk_data, crc))

    if organic and not exif_replaced:
        from metascrub.injector import make_organic_exif_blob
        ihdr = clean_chunks[0][1]
        width = struct.unpack('>I', ihdr[0:4])[0]
        height = struct.unpack('>I', ihdr[4:8])[0]
        exif_data = make_organic_exif_blob(width, height)
        if exif_data.startswith(b'Exif\x00\x00'):
            exif_data = exif_data[6:]
        new_chunk = make_chunk(b'eXIf', exif_data)
        insert_idx = len(clean_chunks)
        for i, (ct, _, _) in enumerate(clean_chunks):
            if ct == b'IDAT':
                insert_idx = i
                break
        clean_chunks.insert(insert_idx, new_chunk)

    return rebuild_png(clean_chunks)
