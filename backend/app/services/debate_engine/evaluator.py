"""
AURA Debate Evaluator
Evaluation logic for debate rounds and verdicts
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.logging import logger


class DebateEvaluator:
    """
    Evaluates debate rounds and calculates scores.
    Provides scoring metrics for agent performance.
    """
    
    # Scoring weights
    WEIGHTS = {
        "argument_strength": 0.25,
        "evidence_quality": 0.30,
        "logical_consistency": 0.20,
        "source_reliability": 0.25
    }
    
    def __init__(self):
        pass
    
    def score_exchange(self, exchange: Dict) -> Dict[str, float]:
        """Score a single exchange/argument."""
        argument = exchange.get("argument", exchange.get("analysis", ""))
        agent = exchange.get("agent", "unknown")
        
        scores = {
            "argument_strength": self._score_argument_strength(argument),
            "evidence_quality": self._score_evidence_quality(exchange),
            "logical_consistency": self._score_logical_consistency(argument),
            "source_reliability": self._score_source_reliability(exchange)
        }
        
        # Calculate weighted total
        weighted_total = sum(
            scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS
        )
        
        return {
            **scores,
            "weighted_total": round(weighted_total, 2),
            "agent": agent
        }
    
    def evaluate_round(self, exchanges: List[Dict]) -> Dict[str, Any]:
        """Evaluate a complete round."""
        scores_by_agent = {"for": [], "against": [], "neutral": []}
        
        for ex in exchanges:
            agent = ex.get("agent", "unknown")
            if agent in scores_by_agent:
                score = self.score_exchange(ex)
                scores_by_agent[agent].append(score)
        
        # Aggregate scores per agent
        agent_totals = {}
        for agent, scores in scores_by_agent.items():
            if scores:
                avg_total = sum(s["weighted_total"] for s in scores) / len(scores)
                agent_totals[agent] = {
                    "exchanges": len(scores),
                    "average_score": round(avg_total, 2),
                    "individual_scores": scores
                }
            else:
                agent_totals[agent] = {
                    "exchanges": 0,
                    "average_score": 5.0
                }
        
        # Determine round winner
        for_score = agent_totals.get("for", {}).get("average_score", 5)
        against_score = agent_totals.get("against", {}).get("average_score", 5)
        
        if against_score > for_score + 0.5:
            winner = "against"
            margin = "decisive" if against_score > for_score + 1.5 else "narrow"
        elif for_score > against_score + 0.5:
            winner = "for"
            margin = "decisive" if for_score > against_score + 1.5 else "narrow"
        else:
            winner = "tie"
            margin = "even"
        
        return {
            "agent_scores": agent_totals,
            "round_winner": winner,
            "margin": margin,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def calculate_final_scores(
        self,
        round_evaluations: List[Dict]
    ) -> Dict[str, float]:
        """Calculate cumulative scores across all rounds."""
        totals = {"for": 0, "against": 0, "neutral": 0}
        
        for rd in round_evaluations:
            scores = rd.get("agent_scores", {})
            for agent, data in scores.items():
                if agent in totals:
                    totals[agent] += data.get("average_score", 5)
        
        return {k: round(v, 1) for k, v in totals.items()}
    
    def determine_verdict(
        self,
        final_scores: Dict[str, float],
        quick_classification: Dict = None
    ) -> Dict[str, Any]:
        """Determine final verdict based on debate outcome."""
        for_score = final_scores.get("for", 0)
        against_score = final_scores.get("against", 0)
        
        # Factor in quick classification
        quick_verdict = quick_classification.get("verdict") if quick_classification else None
        quick_confidence = quick_classification.get("confidence", 0) if quick_classification else 0
        
        # Determine verdict
        if against_score > for_score + 5:
            verdict = "FALSE"
            confidence = min(0.95, 0.7 + (against_score - for_score) / 50)
        elif against_score > for_score + 2:
            verdict = "FALSE"
            confidence = min(0.85, 0.6 + (against_score - for_score) / 40)
        elif for_score > against_score + 5:
            verdict = "TRUE"
            confidence = min(0.90, 0.65 + (for_score - against_score) / 50)
        elif for_score > against_score + 2:
            verdict = "TRUE"
            confidence = min(0.75, 0.55 + (for_score - against_score) / 40)
        elif abs(for_score - against_score) < 1:
            verdict = "UNVERIFIABLE"
            confidence = 0.5
        else:
            verdict = "MISLEADING"
            confidence = 0.6
        
        # Adjust based on quick classification agreement
        if quick_verdict and quick_confidence > 0.7:
            if (quick_verdict == "FAKE" and verdict == "FALSE") or \
               (quick_verdict == "REAL" and verdict == "TRUE"):
                confidence = min(confidence + 0.1, 0.98)
        
        return {
            "verdict": verdict,
            "confidence": round(confidence, 2),
            "debate_scores": final_scores,
            "quick_classification_agreement": quick_verdict == verdict if quick_verdict else None
        }
    
    def _score_argument_strength(self, argument: str) -> float:
        """Score argument strength (1-10)."""
        if not argument:
            return 3.0
        
        score = 5.0  # Base
        
        # Length (longer = more detailed = higher)
        words = len(argument.split())
        if words > 200:
            score += 1.5
        elif words > 100:
            score += 1.0
        elif words < 50:
            score -= 1.0
        
        # Contains structured points
        if any(marker in argument for marker in ["1.", "2.", "- ", "* ", "firstly", "secondly"]):
            score += 1.0
        
        # Contains assertions
        if any(w in argument.lower() for w in ["therefore", "because", "evidence", "shows"]):
            score += 0.5
        
        return min(max(score, 1), 10)
    
    def _score_evidence_quality(self, exchange: Dict) -> float:
        """Score evidence quality (1-10)."""
        evidence_cited = exchange.get("evidence_cited", [])
        argument = exchange.get("argument", "")
        
        score = 5.0
        
        # Evidence count
        score += min(len(evidence_cited), 3)
        
        # Mentions authoritative sources
        trusted = ["who", "cdc", "reuters", "pib.gov", "government", "study", "research"]
        mentions = sum(1 for t in trusted if t in argument.lower())
        score += min(mentions, 2)
        
        return min(max(score, 1), 10)
    
    def _score_logical_consistency(self, argument: str) -> float:
        """Score logical consistency (1-10)."""
        if not argument:
            return 3.0
        
        score = 6.0  # Base - assume reasonable
        
        # Check for logical connectors
        connectors = ["however", "but", "therefore", "thus", "because", "since", "although"]
        connector_count = sum(1 for c in connectors if c in argument.lower())
        score += min(connector_count * 0.5, 2)
        
        # Penalize contradictions
        if "however" in argument.lower() and "but" in argument.lower():
            score -= 0.5  # Might be hedging
        
        return min(max(score, 1), 10)
    
    def _score_source_reliability(self, exchange: Dict) -> float:
        """Score source reliability (1-10)."""
        argument = exchange.get("argument", "")
        evidence = exchange.get("evidence_cited", [])
        
        score = 5.0
        
        # Check for specific authoritative sources
        high_trust = ["who.int", "cdc.gov", "reuters", "government", "peer-reviewed"]
        for source in high_trust:
            if source in argument.lower():
                score += 1.0
        
        # Check evidence sources
        for e in evidence:
            if e.get("is_trusted") or e.get("domain_authority", 0) > 80:
                score += 0.5
        
        return min(max(score, 1), 10)


# Global instance
debate_evaluator = DebateEvaluator()
