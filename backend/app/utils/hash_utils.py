import hashlib

def calculate_sha256(file_obj):
    """
    Calculate SHA-256 hash of a file-like object (streaming, chunked).
    :param file_obj: file-like object from Flask (e.g., request.files['file'])
    :return: Hex digest string of SHA-256 hash
    """
    sha256 = hashlib.sha256()
    file_obj.seek(0)  # Ensure you're at the beginning of the file

    for chunk in iter(lambda: file_obj.read(4096), b""):
        sha256.update(chunk)

    file_obj.seek(0)  # Reset stream pointer after reading
    return sha256.hexdigest()