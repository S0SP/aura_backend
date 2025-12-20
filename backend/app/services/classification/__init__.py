"""
AURA Classification Service Package
XLM-RoBERTa based fact classification
"""

from app.services.classification.classifier import classifier, Classifier
from app.services.classification.claim_categorizer import claim_categorizer, ClaimCategorizer

__all__ = [
    "classifier", "Classifier",
    "claim_categorizer", "ClaimCategorizer"
]
