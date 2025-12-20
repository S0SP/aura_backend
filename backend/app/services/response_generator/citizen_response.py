"""
AURA Citizen Response Generator
Simple, user-friendly fact-check responses
"""

from typing import Dict, Any, Optional
from datetime import datetime

from app.core.logging import logger


class CitizenResponse:
    """
    Generates simple, citizen-friendly fact-check responses.
    Uses emojis and clear language for easy understanding.
    """
    
    VERDICT_EMOJI = {
        "TRUE": "✅",
        "FALSE": "❌",
        "MISLEADING": "⚠️",
        "UNVERIFIABLE": "❓"
    }
    
    VERDICT_HINDI = {
        "TRUE": "सच",
        "FALSE": "झूठ",
        "MISLEADING": "भ्रामक",
        "UNVERIFIABLE": "असत्यापित"
    }
    
    def __init__(self):
        pass
    
    def generate(
        self,
        claim: str,
        verdict: str,
        confidence: float,
        reasoning: str,
        key_evidence: list = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Generate citizen-friendly response.
        """
        emoji = self.VERDICT_EMOJI.get(verdict, "🔍")
        confidence_pct = int(confidence * 100)
        
        # Generate simple summary
        if language == "hi":
            response_text = self._generate_hindi(
                claim, verdict, confidence_pct, reasoning, key_evidence
            )
        else:
            response_text = self._generate_english(
                claim, verdict, confidence_pct, reasoning, key_evidence
            )
        
        # Generate social sharing text
        share_text = self._generate_share_text(claim, verdict, emoji)
        
        return {
            "type": "citizen",
            "claim": claim,
            "verdict": verdict,
            "verdict_emoji": emoji,
            "confidence_percent": confidence_pct,
            "response_text": response_text,
            "share_text": share_text,
            "language": language,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _generate_english(
        self,
        claim: str,
        verdict: str,
        confidence: int,
        reasoning: str,
        key_evidence: list
    ) -> str:
        """Generate English response."""
        emoji = self.VERDICT_EMOJI.get(verdict, "🔍")
        
        response = f"""
{emoji} **VERDICT: {verdict}**

📝 **You asked about:**
"{claim[:200]}{"..." if len(claim) > 200 else ""}"

📊 **Our confidence:** {confidence}%

📖 **What we found:**
{reasoning[:400]}{"..." if len(reasoning) > 400 else ""}
"""
        
        if key_evidence:
            response += "\n🔗 **Key sources checked:**\n"
            for i, ev in enumerate(key_evidence[:3], 1):
                if isinstance(ev, dict):
                    source = ev.get("source", ev.get("title", "Unknown source"))
                else:
                    source = str(ev)[:50]
                response += f"  {i}. {source}\n"
        
        # Add helpful tip based on verdict
        if verdict == "FALSE":
            response += "\n⚠️ **Tip:** This claim is FALSE. Please don't share it further!"
        elif verdict == "TRUE":
            response += "\n✅ **Tip:** This appears to be accurate information."
        elif verdict == "MISLEADING":
            response += "\n⚠️ **Tip:** This claim contains some truth but is misleading. Read carefully!"
        else:
            response += "\n❓ **Tip:** We couldn't fully verify this. Check trusted sources before sharing."
        
        return response.strip()
    
    def _generate_hindi(
        self,
        claim: str,
        verdict: str,
        confidence: int,
        reasoning: str,
        key_evidence: list
    ) -> str:
        """Generate Hindi response."""
        emoji = self.VERDICT_EMOJI.get(verdict, "🔍")
        hindi_verdict = self.VERDICT_HINDI.get(verdict, verdict)
        
        response = f"""
{emoji} **फैसला: {hindi_verdict}**

📝 **आपने पूछा:**
"{claim[:200]}{"..." if len(claim) > 200 else ""}"

📊 **विश्वसनीयता:** {confidence}%

📖 **हमने क्या पाया:**
{reasoning[:400]}{"..." if len(reasoning) > 400 else ""}
"""
        
        if verdict == "FALSE":
            response += "\n⚠️ **सुझाव:** यह दावा झूठा है। कृपया इसे आगे न बढ़ाएं!"
        elif verdict == "TRUE":
            response += "\n✅ **सुझाव:** यह सही जानकारी प्रतीत होती है।"
        
        return response.strip()
    
    def _generate_share_text(self, claim: str, verdict: str, emoji: str) -> str:
        """Generate shareable text."""
        claim_short = claim[:100] + "..." if len(claim) > 100 else claim
        return f"{emoji} AURA Fact-Check: \"{claim_short}\" is {verdict}. Check facts before sharing! #AURAFactCheck"


# Global instance
citizen_response = CitizenResponse()
