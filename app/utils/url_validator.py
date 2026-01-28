from urllib.parse import urlparse
from fastapi import HTTPException


def validate_url(url: str) -> str:
    """
    Validate and normalize URL.
    Adds https:// if no scheme provided.
    Raises HTTPException if URL is invalid.

    Args:
        url: URL string to validate

    Returns:
        Normalized URL with scheme

    Raises:
        HTTPException: If URL is invalid
    """
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    url = url.strip()

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        parsed = urlparse(url)

        if parsed.scheme not in ["http", "https"]:
            raise HTTPException(status_code=400, detail="URL must use http or https")

        if not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL format")

        if "." not in parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid domain")

        return url

    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=400, detail=f"Invalid URL: {str(e)}")