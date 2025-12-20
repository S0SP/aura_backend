"""
AURA Service - Response Generator
Generates citizen and journalist responses from verification results
"""

from typing import Dict, Any, Optional
from datetime import datetime

from app.core.logging import logger
from app.core.config import settings
from app.services.llm_service import get_llm
from app.models.verification import VerdictType


class ResponseGenerator:
    """Generates human-readable responses for different audiences."""
    
    # Response templates by verdict
    CITIZEN_TEMPLATES = {
        VerdictType.TRUE: "✅ **This claim appears to be TRUE.**\n\n{reasoning}\n\n📊 Confidence: {confidence}%",
        VerdictType.FALSE: "❌ **This claim appears to be FALSE.**\n\n{reasoning}\n\n📊 Confidence: {confidence}%",
        VerdictType.MISLEADING: "⚠️ **This claim is MISLEADING.**\n\n{reasoning}\n\n📊 Confidence: {confidence}%",
        VerdictType.PARTIALLY_TRUE: "🔶 **This claim is PARTIALLY TRUE.**\n\n{reasoning}\n\n📊 Confidence: {confidence}%",
        VerdictType.UNVERIFIABLE: "❓ **This claim is UNVERIFIABLE.**\n\n{reasoning}\n\n📊 Confidence: {confidence}%"
    }
    
    JOURNALIST_SECTIONS = [
        "executive_summary",
        "claim_analysis",
        "evidence_review",
        "source_assessment",
        "verdict_rationale",
        "recommendations"
    ]
    
    async def generate_citizen_response(
        self,
        claim: str,
        verdict: str,
        confidence: float,
        reasoning_summary: str,
        key_points: list = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Generate a simple, accessible response for citizens.
        
        Args:
            claim: Original claim
            verdict: Verification verdict
            confidence: Confidence score (0-1)
            reasoning_summary: Brief reasoning
            key_points: Key supporting points
            language: Response language
            
        Returns:
            Citizen-friendly response
        """
        try:
            verdict_type = VerdictType(verdict) if isinstance(verdict, str) else verdict
        except ValueError:
            verdict_type = VerdictType.UNVERIFIABLE
        
        template = self.CITIZEN_TEMPLATES.get(
            verdict_type, 
            self.CITIZEN_TEMPLATES[VerdictType.UNVERIFIABLE]
        )
        
        # Build key points section
        points_text = ""
        if key_points:
            points_text = "\n\n**Key Points:**\n" + "\n".join(f"• {p}" for p in key_points[:3])
        
        response_text = template.format(
            reasoning=reasoning_summary,
            confidence=int(confidence * 100)
        ) + points_text
        
        # Add action recommendation
        action = self._get_action_recommendation(verdict_type)
        response_text += f"\n\n💡 **What to do:** {action}"
        
        return {
            "format": "citizen",
            "language": language,
            "verdict": verdict,
            "verdict_emoji": self._get_verdict_emoji(verdict_type),
            "response_text": response_text,
            "response_html": self._to_html(response_text),
            "shareable_summary": self._get_shareable_summary(claim, verdict_type, confidence),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def generate_journalist_response(
        self,
        claim: str,
        verdict: str,
        confidence: float,
        reasoning_detailed: str,
        evidence_items: list = None,
        debate_summary: dict = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Generate a detailed, analytical response for journalists.
        
        Args:
            claim: Original claim
            verdict: Verification verdict
            confidence: Confidence score
            reasoning_detailed: Detailed reasoning
            evidence_items: List of evidence used
            debate_summary: Summary of debate
            language: Response language
            
        Returns:
            Journalist-oriented detailed report
        """
        llm = get_llm()
        
        prompt = f"""Generate a professional fact-check report for journalists.

CLAIM: "{claim}"

VERDICT: {verdict}
CONFIDENCE: {int(confidence * 100)}%

DETAILED REASONING:
{reasoning_detailed}

EVIDENCE USED:
{self._format_evidence(evidence_items)}

DEBATE SUMMARY:
{str(debate_summary) if debate_summary else 'No debate conducted'}

Generate a structured report with these sections:
1. EXECUTIVE SUMMARY (2-3 sentences)
2. CLAIM ANALYSIS (what the claim asserts, context)
3. EVIDENCE REVIEW (key sources, credibility assessment)
4. SOURCE ASSESSMENT (reliability of sources cited)
5. VERDICT RATIONALE (why this verdict was reached)
6. RECOMMENDATIONS (for responsible reporting)

Format as professional markdown suitable for publication."""
        
        if llm:
            try:
                response = await llm.ainvoke(prompt)
                report_text = response.content if hasattr(response, 'content') else str(response)
            except Exception as e:
                logger.error(f"LLM report generation failed: {e}")
                report_text = self._fallback_journalist_report(
                    claim, verdict, confidence, reasoning_detailed
                )
        else:
            report_text = self._fallback_journalist_report(
                claim, verdict, confidence, reasoning_detailed
            )
        
        return {
            "format": "journalist",
            "language": language,
            "verdict": verdict,
            "confidence_percent": int(confidence * 100),
            "report_markdown": report_text,
            "report_html": self._to_html(report_text),
            "evidence_count": len(evidence_items) if evidence_items else 0,
            "methodology": "Multi-agent debate with evidence retrieval",
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def generate_government_alert(
        self,
        claim: str,
        verdict: str,
        confidence: float,
        severity: str = "medium",
        affected_regions: list = None,
        category: str = "other"
    ) -> Dict[str, Any]:
        """
        Generate a CAP-format alert for government portals.
        
        Args:
            claim: The misinformation claim
            verdict: Verification verdict
            confidence: Confidence score
            severity: Alert severity (low, medium, high, critical)
            affected_regions: List of affected regions/states
            category: Claim category
            
        Returns:
            CAP-format alert
        """
        alert_id = f"AURA-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Determine urgency based on severity and category
        urgency_map = {
            "critical": "Immediate",
            "high": "Expected",
            "medium": "Future",
            "low": "Past"
        }
        
        severity_map = {
            "critical": "Extreme",
            "high": "Severe",
            "medium": "Moderate",
            "low": "Minor"
        }
        
        return {
            "format": "cap_alert",
            "alert": {
                "identifier": alert_id,
                "sender": "aura-factchecker@gov.in",
                "sent": datetime.utcnow().isoformat(),
                "status": "Actual",
                "msgType": "Alert",
                "scope": "Public",
                "info": {
                    "category": self._map_to_cap_category(category),
                    "event": "Misinformation Alert",
                    "urgency": urgency_map.get(severity, "Future"),
                    "severity": severity_map.get(severity, "Moderate"),
                    "certainty": self._confidence_to_certainty(confidence),
                    "headline": f"[{verdict}] Misinformation detected",
                    "description": claim,
                    "area": {
                        "areaDesc": ", ".join(affected_regions) if affected_regions else "All India"
                    }
                }
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _get_verdict_emoji(self, verdict: VerdictType) -> str:
        emojis = {
            VerdictType.TRUE: "✅",
            VerdictType.FALSE: "❌",
            VerdictType.MISLEADING: "⚠️",
            VerdictType.PARTIALLY_TRUE: "🔶",
            VerdictType.UNVERIFIABLE: "❓"
        }
        return emojis.get(verdict, "❓")
    
    def _get_action_recommendation(self, verdict: VerdictType) -> str:
        actions = {
            VerdictType.TRUE: "You can share this information with confidence.",
            VerdictType.FALSE: "Please do not share this. Consider alerting others who might have seen it.",
            VerdictType.MISLEADING: "Exercise caution when sharing. The context may be distorted.",
            VerdictType.PARTIALLY_TRUE: "Some parts are accurate, but verify the full context before sharing.",
            VerdictType.UNVERIFIABLE: "We couldn't verify this claim. Wait for more information before sharing."
        }
        return actions.get(verdict, "Exercise caution before sharing.")
    
    def _get_shareable_summary(self, claim: str, verdict: VerdictType, confidence: float) -> str:
        emoji = self._get_verdict_emoji(verdict)
        return f"{emoji} Claim: \"{claim[:80]}...\" - {verdict.value} ({int(confidence*100)}% confidence) - Verified by AURA"
    
    def _format_evidence(self, evidence: list) -> str:
        if not evidence:
            return "No evidence items provided"
        return "\n".join([
            f"- {e.get('title', 'Source')}: {e.get('content_snippet', '')[:150]}"
            for e in evidence[:5]
        ])
    
    def _to_html(self, markdown: str) -> str:
        """Simple markdown to HTML conversion."""
        # Basic conversion - in production use a proper markdown library
        html = markdown
        html = html.replace("**", "<strong>").replace("**", "</strong>")
        html = html.replace("\n\n", "</p><p>")
        html = html.replace("\n", "<br>")
        return f"<p>{html}</p>"
    
    def _fallback_journalist_report(
        self, claim: str, verdict: str, confidence: float, reasoning: str
    ) -> str:
        return f"""# Fact-Check Report

## Executive Summary
Claim: "{claim}"
Verdict: **{verdict}** (Confidence: {int(confidence*100)}%)

## Analysis
{reasoning}

## Methodology
This claim was verified using AURA's multi-agent debate system with automated evidence retrieval.

---
*Generated by AURA Fact-Checker*
"""
    
    def _map_to_cap_category(self, category: str) -> str:
        mapping = {
            "health": "Health",
            "political": "Security",
            "financial": "Env",
            "disaster": "Met",
            "social": "Safety"
        }
        return mapping.get(category, "Other")
    
    def _confidence_to_certainty(self, confidence: float) -> str:
        if confidence >= 0.9:
            return "Observed"
        elif confidence >= 0.7:
            return "Likely"
        elif confidence >= 0.5:
            return "Possible"
        else:
            return "Unlikely"


# Global instance
response_generator = ResponseGenerator()
