from metascrub.injector import (
    make_organic_exif_blob,
    make_design_exif_blob,
    make_custom_exif_blob,
    make_canva_exif_blob,
    CAMERA_PROFILES,
    DESIGN_APP_PROFILES,
)


class TestMakeOrganicExifBlob:
    def test_returns_bytes(self):
        blob = make_organic_exif_blob()
        assert isinstance(blob, bytes)
        assert len(blob) > 0

    def test_starts_with_exif_header(self):
        blob = make_organic_exif_blob()
        assert blob.startswith(b"Exif\x00\x00")

    def test_parseable_by_piexif(self):
        import piexif
        blob = make_organic_exif_blob(1920, 1080)
        exif = piexif.load(blob)
        assert "0th" in exif
        assert "Exif" in exif
        make_val = exif["0th"].get(piexif.ImageIFD.Make)
        assert make_val is not None

    def test_includes_dimensions_when_provided(self):
        import piexif
        blob = make_organic_exif_blob(1920, 1080)
        exif = piexif.load(blob)
        assert exif["Exif"][piexif.ExifIFD.PixelXDimension] == 1920
        assert exif["Exif"][piexif.ExifIFD.PixelYDimension] == 1080

    def test_different_camera_profiles(self):
        makes = set()
        for _ in range(20):
            blob = make_organic_exif_blob()
            import piexif
            exif = piexif.load(blob)
            make = exif["0th"].get(piexif.ImageIFD.Make, b"").decode()
            makes.add(make)
        assert len(makes) > 1  # at least some variation


class TestMakeDesignExifBlob:
    def test_returns_bytes(self):
        blob = make_design_exif_blob()
        assert isinstance(blob, bytes)

    def test_parseable_by_piexif(self):
        import piexif
        blob = make_design_exif_blob(800, 600)
        exif = piexif.load(blob)
        assert "0th" in exif
        software = exif["0th"].get(piexif.ImageIFD.Software)
        assert software is not None

    def test_known_design_apps(self):
        import piexif
        app_names = {p["software"] for p in DESIGN_APP_PROFILES}
        found = set()
        for _ in range(50):
            blob = make_design_exif_blob()
            exif = piexif.load(blob)
            sw = exif["0th"].get(piexif.ImageIFD.Software, b"").decode()
            found.add(sw)
        assert found.issubset(app_names)


class TestMakeCustomExifBlob:
    def test_returns_bytes(self):
        blob = make_custom_exif_blob()
        assert isinstance(blob, bytes)

    def test_custom_make(self):
        import piexif
        blob = make_custom_exif_blob(make="Nikon")
        exif = piexif.load(blob)
        assert exif["0th"][piexif.ImageIFD.Make] == b"Nikon"

    def test_custom_model(self):
        import piexif
        blob = make_custom_exif_blob(model="D850")
        exif = piexif.load(blob)
        assert exif["0th"][piexif.ImageIFD.Model] == b"D850"

    def test_iso_zero_uses_random(self):
        import piexif
        blob = make_custom_exif_blob(iso=0)
        exif = piexif.load(blob)
        iso_val = exif["Exif"][piexif.ExifIFD.ISOSpeedRatings]
        assert iso_val > 0  # should have picked a random iso > 0

    def test_custom_iso(self):
        import piexif
        blob = make_custom_exif_blob(iso=400)
        exif = piexif.load(blob)
        assert exif["Exif"][piexif.ExifIFD.ISOSpeedRatings] == 400

    def test_custom_date_str(self):
        import piexif
        blob = make_custom_exif_blob(date_str="2024:01:15 14:30:00")
        exif = piexif.load(blob)
        assert exif["Exif"][piexif.ExifIFD.DateTimeOriginal] == b"2024:01:15 14:30:00"

    def test_custom_fnumber(self):
        import piexif
        blob = make_custom_exif_blob(fnumber=(28, 10))
        exif = piexif.load(blob)
        fn = exif["Exif"][piexif.ExifIFD.FNumber]
        assert fn == (28, 10)

    def test_custom_shutter(self):
        import piexif
        blob = make_custom_exif_blob(shutter=(1, 500))
        exif = piexif.load(blob)
        et = exif["Exif"][piexif.ExifIFD.ExposureTime]
        assert et == (1, 500)

    def test_custom_focal(self):
        import piexif
        blob = make_custom_exif_blob(focal=(85, 1))
        exif = piexif.load(blob)
        fl = exif["Exif"][piexif.ExifIFD.FocalLength]
        assert fl == (85, 1)


class TestMakeCanvaExifBlob:
    def test_returns_bytes(self):
        blob = make_canva_exif_blob()
        assert isinstance(blob, bytes)

    def test_canva_is_make_and_model(self):
        import piexif
        blob = make_canva_exif_blob()
        exif = piexif.load(blob)
        assert exif["0th"][piexif.ImageIFD.Make] == b"Canva"
        assert exif["0th"][piexif.ImageIFD.Model] == b"Canva"


class TestCameraProfiles:
    def test_has_required_fields(self):
        for profile in CAMERA_PROFILES:
            assert "make" in profile
            assert "model" in profile
            assert "lens" in profile

    def test_known_makes(self):
        makes = {p["make"] for p in CAMERA_PROFILES}
        assert "Canon" in makes
        assert "Nikon" in makes
        assert "SONY" in makes
        assert "FUJIFILM" in makes
