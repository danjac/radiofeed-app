import hashlib


def make_content_hash(content):
    """Hashes content to a hex string.

    Args:
        content (bytes)

    Returns:
        str
    """
    return hashlib.sha256(content).hexdigest()
