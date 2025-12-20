"""
AURA Language Detector
Multi-language detection for claims and content
"""

from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
from enum import Enum


class SupportedLanguage(str, Enum):
    """Languages supported by AURA."""
    ENGLISH = "en"
    HINDI = "hi"
    MARATHI = "mr"
    TAMIL = "ta"
    TELUGU = "te"
    BENGALI = "bn"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    PORTUGUESE = "pt"
    ARABIC = "ar"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    RUSSIAN = "ru"
    UNKNOWN = "unknown"


@dataclass
class LanguageDetectionResult:
    """Result of language detection."""
    language: str
    confidence: float
    language_name: str
    is_supported: bool
    alternatives: List[Dict[str, float]] = None


# Language name mapping
LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "ar": "Arabic",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ru": "Russian",
    "unknown": "Unknown"
}

# Supported languages set for quick lookup
SUPPORTED_LANGUAGES = {lang.value for lang in SupportedLanguage if lang != SupportedLanguage.UNKNOWN}


def detect_language(text: str) -> LanguageDetectionResult:
    """
    Detect the language of given text.
    
    Uses langdetect as primary and lingua as fallback for better accuracy.
    
    Args:
        text: Text to detect language for
        
    Returns:
        LanguageDetectionResult with detected language and confidence
    """
    if not text or len(text.strip()) < 3:
        return LanguageDetectionResult(
            language="unknown",
            confidence=0.0,
            language_name="Unknown",
            is_supported=False
        )
    
    try:
        # Try langdetect first (fast)
        from langdetect import detect_langs, LangDetectException
        
        try:
            detections = detect_langs(text)
            
            if detections:
                top_detection = detections[0]
                lang_code = top_detection.lang
                confidence = top_detection.prob
                
                # Get alternatives
                alternatives = [
                    {"language": d.lang, "confidence": round(d.prob, 3)}
                    for d in detections[1:4]
                ]
                
                return LanguageDetectionResult(
                    language=lang_code,
                    confidence=round(confidence, 3),
                    language_name=LANGUAGE_NAMES.get(lang_code, lang_code.upper()),
                    is_supported=lang_code in SUPPORTED_LANGUAGES,
                    alternatives=alternatives
                )
        except LangDetectException:
            pass
        
        # Fallback: Use lingua for better accuracy with Indian languages
        try:
            from lingua import Language, LanguageDetectorBuilder
            
            # Build detector with priority languages
            detector = LanguageDetectorBuilder.from_languages(
                Language.ENGLISH, Language.HINDI, Language.MARATHI,
                Language.TAMIL, Language.TELUGU, Language.BENGALI,
                Language.GUJARATI, Language.SPANISH, Language.FRENCH
            ).build()
            
            result = detector.detect_language_of(text)
            
            if result:
                lang_code = result.iso_code_639_1.name.lower()
                confidence_values = detector.compute_language_confidence_values(text)
                confidence = confidence_values[0].value if confidence_values else 0.5
                
                return LanguageDetectionResult(
                    language=lang_code,
                    confidence=round(confidence, 3),
                    language_name=LANGUAGE_NAMES.get(lang_code, lang_code.upper()),
                    is_supported=lang_code in SUPPORTED_LANGUAGES
                )
        except ImportError:
            pass
        except Exception:
            pass
        
    except ImportError:
        # If langdetect is not installed, use simple heuristics
        return _detect_language_heuristic(text)
    except Exception as e:
        pass
    
    return LanguageDetectionResult(
        language="unknown",
        confidence=0.0,
        language_name="Unknown",
        is_supported=False
    )


def _detect_language_heuristic(text: str) -> LanguageDetectionResult:
    """
    Simple heuristic-based language detection.
    Used as fallback when libraries are not available.
    """
    # Script-based detection
    
    # Devanagari (Hindi, Marathi)
    if any('\u0900' <= char <= '\u097F' for char in text):
        # Check for Marathi-specific characters
        if any(char in text for char in ['ळ', 'ऱ']):
            return LanguageDetectionResult(
                language="mr",
                confidence=0.7,
                language_name="Marathi",
                is_supported=True
            )
        return LanguageDetectionResult(
            language="hi",
            confidence=0.7,
            language_name="Hindi",
            is_supported=True
        )
    
    # Tamil
    if any('\u0B80' <= char <= '\u0BFF' for char in text):
        return LanguageDetectionResult(
            language="ta",
            confidence=0.8,
            language_name="Tamil",
            is_supported=True
        )
    
    # Telugu
    if any('\u0C00' <= char <= '\u0C7F' for char in text):
        return LanguageDetectionResult(
            language="te",
            confidence=0.8,
            language_name="Telugu",
            is_supported=True
        )
    
    # Bengali
    if any('\u0980' <= char <= '\u09FF' for char in text):
        return LanguageDetectionResult(
            language="bn",
            confidence=0.8,
            language_name="Bengali",
            is_supported=True
        )
    
    # Gujarati
    if any('\u0A80' <= char <= '\u0AFF' for char in text):
        return LanguageDetectionResult(
            language="gu",
            confidence=0.8,
            language_name="Gujarati",
            is_supported=True
        )
    
    # Kannada
    if any('\u0C80' <= char <= '\u0CFF' for char in text):
        return LanguageDetectionResult(
            language="kn",
            confidence=0.8,
            language_name="Kannada",
            is_supported=True
        )
    
    # Malayalam
    if any('\u0D00' <= char <= '\u0D7F' for char in text):
        return LanguageDetectionResult(
            language="ml",
            confidence=0.8,
            language_name="Malayalam",
            is_supported=True
        )
    
    # Arabic
    if any('\u0600' <= char <= '\u06FF' for char in text):
        return LanguageDetectionResult(
            language="ar",
            confidence=0.8,
            language_name="Arabic",
            is_supported=True
        )
    
    # Chinese
    if any('\u4E00' <= char <= '\u9FFF' for char in text):
        return LanguageDetectionResult(
            language="zh",
            confidence=0.8,
            language_name="Chinese",
            is_supported=True
        )
    
    # Japanese (Hiragana/Katakana)
    if any(('\u3040' <= char <= '\u309F') or ('\u30A0' <= char <= '\u30FF') for char in text):
        return LanguageDetectionResult(
            language="ja",
            confidence=0.8,
            language_name="Japanese",
            is_supported=True
        )
    
    # Korean
    if any('\uAC00' <= char <= '\uD7AF' for char in text):
        return LanguageDetectionResult(
            language="ko",
            confidence=0.8,
            language_name="Korean",
            is_supported=True
        )
    
    # Cyrillic (Russian)
    if any('\u0400' <= char <= '\u04FF' for char in text):
        return LanguageDetectionResult(
            language="ru",
            confidence=0.8,
            language_name="Russian",
            is_supported=True
        )
    
    # Default to English for Latin script
    if text.isascii() or any('a' <= char.lower() <= 'z' for char in text):
        return LanguageDetectionResult(
            language="en",
            confidence=0.5,
            language_name="English",
            is_supported=True
        )
    
    return LanguageDetectionResult(
        language="unknown",
        confidence=0.0,
        language_name="Unknown",
        is_supported=False
    )


def get_language_name(code: str) -> str:
    """Get full language name from code."""
    return LANGUAGE_NAMES.get(code, code.upper())


def is_language_supported(code: str) -> bool:
    """Check if a language code is supported."""
    return code in SUPPORTED_LANGUAGES


def get_supported_languages() -> List[Dict[str, str]]:
    """Get list of all supported languages."""
    return [
        {"code": lang.value, "name": LANGUAGE_NAMES.get(lang.value, lang.value)}
        for lang in SupportedLanguage
        if lang != SupportedLanguage.UNKNOWN
    ]
