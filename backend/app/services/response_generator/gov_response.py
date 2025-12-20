"""
AURA Government Response Generator
CAP format alerts for government agencies
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import xml.etree.ElementTree as ET
from uuid import uuid4

from app.core.logging import logger


class GovResponse:
    """
    Generates government-formatted responses in CAP (Common Alerting Protocol).
    For government agencies monitoring misinformation.
    """
    
    # CAP severity mappings
    SEVERITY_MAP = {
        "FALSE": "Severe",
        "MISLEADING": "Moderate",
        "UNVERIFIABLE": "Minor",
        "TRUE": "Unknown"
    }
    
    URGENCY_MAP = {
        "FALSE": "Immediate",
        "MISLEADING": "Expected",
        "UNVERIFIABLE": "Future",
        "TRUE": "Past"
    }
    
    def __init__(self):
        pass
    
    def generate(
        self,
        claim: str,
        verdict: str,
        confidence: float,
        reasoning: str,
        category: str = None,
        is_indian_context: bool = True,
        evidence: List[Dict] = None,
        verification_id: str = None
    ) -> Dict[str, Any]:
        """
        Generate government CAP-formatted alert.
        """
        alert_id = f"AURA-{datetime.utcnow().strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"
        
        # Generate CAP XML
        cap_xml = self._generate_cap_xml(
            alert_id=alert_id,
            claim=claim,
            verdict=verdict,
            confidence=confidence,
            reasoning=reasoning,
            category=category,
            is_indian_context=is_indian_context
        )
        
        # Generate structured alert data
        alert_data = self._generate_alert_data(
            alert_id=alert_id,
            claim=claim,
            verdict=verdict,
            confidence=confidence,
            reasoning=reasoning,
            category=category,
            is_indian_context=is_indian_context,
            evidence=evidence,
            verification_id=verification_id
        )
        
        return {
            "type": "government",
            "format": "CAP",
            "alert_id": alert_id,
            "verification_id": verification_id,
            "claim": claim,
            "verdict": verdict,
            "severity": self.SEVERITY_MAP.get(verdict, "Unknown"),
            "urgency": self.URGENCY_MAP.get(verdict, "Unknown"),
            "cap_xml": cap_xml,
            "alert_data": alert_data,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _generate_cap_xml(
        self,
        alert_id: str,
        claim: str,
        verdict: str,
        confidence: float,
        reasoning: str,
        category: str,
        is_indian_context: bool
    ) -> str:
        """Generate CAP XML format."""
        # Create root element
        alert = ET.Element("alert", xmlns="urn:oasis:names:tc:emergency:cap:1.2")
        
        # Add mandatory elements
        ET.SubElement(alert, "identifier").text = alert_id
        ET.SubElement(alert, "sender").text = "aura@factchecker.in"
        ET.SubElement(alert, "sent").text = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00")
        ET.SubElement(alert, "status").text = "Actual"
        ET.SubElement(alert, "msgType").text = "Alert"
        ET.SubElement(alert, "scope").text = "Public"
        
        # Add info block
        info = ET.SubElement(alert, "info")
        ET.SubElement(info, "language").text = "en-IN"
        ET.SubElement(info, "category").text = "Security"  # Misinformation
        ET.SubElement(info, "event").text = f"Misinformation Alert: {verdict}"
        ET.SubElement(info, "urgency").text = self.URGENCY_MAP.get(verdict, "Unknown")
        ET.SubElement(info, "severity").text = self.SEVERITY_MAP.get(verdict, "Unknown")
        ET.SubElement(info, "certainty").text = "Likely" if confidence > 0.7 else "Possible"
        
        # Add headline and description
        headline = f"AURA FACT-CHECK: {verdict} - {claim[:50]}..."
        ET.SubElement(info, "headline").text = headline
        ET.SubElement(info, "description").text = reasoning[:500]
        
        # Add area if Indian context
        if is_indian_context:
            area = ET.SubElement(info, "area")
            ET.SubElement(area, "areaDesc").text = "Republic of India"
            ET.SubElement(area, "geocode", valueName="ISO 3166-1").text = "IN"
        
        # Convert to string
        return ET.tostring(alert, encoding="unicode", method="xml")
    
    def _generate_alert_data(
        self,
        alert_id: str,
        claim: str,
        verdict: str,
        confidence: float,
        reasoning: str,
        category: str,
        is_indian_context: bool,
        evidence: List[Dict],
        verification_id: str
    ) -> Dict[str, Any]:
        """Generate structured alert data."""
        # Determine threat level
        if verdict == "FALSE" and confidence > 0.8:
            threat_level = "HIGH"
        elif verdict == "FALSE" or verdict == "MISLEADING":
            threat_level = "MEDIUM"
        else:
            threat_level = "LOW"
        
        return {
            "alert_id": alert_id,
            "verification_id": verification_id,
            "threat_level": threat_level,
            "claim": {
                "text": claim,
                "category": category or "general",
                "is_indian_context": is_indian_context
            },
            "verdict": {
                "result": verdict,
                "confidence": confidence,
                "severity": self.SEVERITY_MAP.get(verdict, "Unknown")
            },
            "analysis": {
                "summary": reasoning[:300],
                "evidence_count": len(evidence) if evidence else 0,
                "key_sources": [
                    e.get("source", "Unknown")[:50] for e in (evidence or [])[:5]
                ]
            },
            "recommendations": self._get_recommendations(verdict, category),
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "generator": "AURA Fact-Checker v1.0",
                "format_version": "CAP 1.2"
            }
        }
    
    def _get_recommendations(self, verdict: str, category: str) -> List[str]:
        """Get recommendations based on verdict and category."""
        recommendations = []
        
        if verdict == "FALSE":
            recommendations.append("Consider issuing counter-messaging through official channels")
            recommendations.append("Monitor for spread on social media platforms")
            if category == "health":
                recommendations.append("Coordinate with Ministry of Health for official clarification")
            elif category == "political":
                recommendations.append("Coordinate with Election Commission if election-related")
        elif verdict == "MISLEADING":
            recommendations.append("Issue clarification with complete context")
            recommendations.append("Monitor for further distortion")
        else:
            recommendations.append("Continue monitoring claimed information")
        
        return recommendations


# Global instance
gov_response = GovResponse()
