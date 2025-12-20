"""
AURA Helper Functions
Common utility functions used across the application
"""

import re
import hashlib
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
import json


def get_utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def get_utc_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def hash_text(text: str, algorithm: str = "sha256") -> str:
    """
    Hash text using specified algorithm.
    
    Args:
        text: Text to hash
        algorithm: Hash algorithm (md5, sha1, sha256)
        
    Returns:
        Hex digest of the hash
    """
    if algorithm == "md5":
        return hashlib.md5(text.encode()).hexdigest()
    elif algorithm == "sha1":
        return hashlib.sha1(text.encode()).hexdigest()
    else:
        return hashlib.sha256(text.encode()).hexdigest()


def clean_text(text: str) -> str:
    """
    Clean and normalize text.
    
    - Removes extra whitespace
    - Removes special characters (keeps punctuation)
    - Normalizes line breaks
    """
    if not text:
        return ""
    
    # Normalize line breaks
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    
    # Replace multiple newlines with double newline
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """
    Truncate text to specified length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].rsplit(' ', 1)[0] + suffix


def extract_urls(text: str) -> List[str]:
    """
    Extract all URLs from text.
    
    Args:
        text: Text to search for URLs
        
    Returns:
        List of URLs found
    """
    url_pattern = re.compile(
        r'https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.-])*)?(?:\?[^\s]*)?'
    )
    return url_pattern.findall(text)


def extract_domain(url: str) -> str:
    """
    Extract domain from URL.
    
    Args:
        url: Full URL
        
    Returns:
        Domain name
    """
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return ""


def is_valid_url(url: str) -> bool:
    """Check if string is a valid URL."""
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    return bool(url_pattern.match(url))


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """Safely parse JSON string."""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """Safely convert object to JSON string."""
    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return default


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """
    Flatten a nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Prefix for keys
        sep: Separator for nested keys
        
    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """
    Split a list into chunks of specified size.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def remove_html_tags(text: str) -> str:
    """Remove HTML tags from text."""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def calculate_reading_time(text: str, words_per_minute: int = 200) -> int:
    """
    Calculate estimated reading time in minutes.
    
    Args:
        text: Text to calculate reading time for
        words_per_minute: Average reading speed
        
    Returns:
        Reading time in minutes
    """
    word_count = len(text.split())
    return max(1, word_count // words_per_minute)


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """
    Mask sensitive data showing only first/last characters.
    
    Args:
        data: Data to mask
        mask_char: Character to use for masking
        visible_chars: Number of characters to keep visible at start/end
        
    Returns:
        Masked string
    """
    if len(data) <= visible_chars * 2:
        return mask_char * len(data)
    
    return data[:visible_chars] + mask_char * (len(data) - visible_chars * 2) + data[-visible_chars:]


def normalize_phone_number(phone: str, default_country_code: str = "+91") -> str:
    """
    Normalize phone number to E.164 format.
    
    Args:
        phone: Phone number string
        default_country_code: Default country code to add
        
    Returns:
        Normalized phone number
    """
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Add country code if not present
    if not cleaned.startswith('+'):
        if cleaned.startswith('0'):
            cleaned = cleaned[1:]
        cleaned = default_country_code + cleaned
    
    return cleaned


def format_bytes(size: int) -> str:
    """Format bytes into human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def get_file_extension(filename: str) -> str:
    """Get file extension from filename."""
    if '.' in filename:
        return filename.rsplit('.', 1)[-1].lower()
    return ""


def is_image_file(filename: str) -> bool:
    """Check if file is an image based on extension."""
    image_extensions = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'}
    return get_file_extension(filename) in image_extensions


def merge_dicts(*dicts: Dict) -> Dict:
    """Merge multiple dictionaries, later ones override earlier."""
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result
