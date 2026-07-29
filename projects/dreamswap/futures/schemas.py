"""
Data schemas - ZERO framework dependencies
Immutable data structures for DREAMSWAP research system.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional
import uuid
import time
@dataclass(frozen=True)
class BookState:
    """Order book snapshot - top 5 levels only."""
    bids: List[Tuple[float, float]] = field(default_factory=list)  # [(price, volume), ...]
    asks: List[Tuple[float, float]] = field(default_factory=list)
    spread: float = 0.0
    imbalance: float = 0.0
    mid: float = 0.0
    timestamp: int = 0
@dataclass(frozen=True)
class FlowState:
    """Participation dynamics."""
    trade_count_1m: int = 0
    trade_count_15m_baseline: float = 0.0
    volume_1m: float = 0.0
    volume_15m_baseline: float = 0.0
    aggressive_volume_1m: float = 0.0
    acceleration_ratio: float = 0.0
    timestamp: int = 0
@dataclass(frozen=True)
class LiquidityState:
    """Liquidity quality metrics."""
    persistence_score: float = 0.0    # 0.0 → 1.0
    cancellation_ratio: float = 0.0
    depth_stability: float = 0.0       # 0.0 → 1.0
    trust_score: float = 0.0          # 0.0 → 1.0
    timestamp: int = 0
@dataclass(frozen=True)
class RegimeState:
    """Market regime classification."""
    primary_regime: str = "NEUTRAL"   # TRENDING_UP / TRENDING_DOWN / RANGING / HIGH_VOL / LOW_VOL
    volatility_regime: str = "NORMAL" # HIGH / NORMAL / LOW
    trend_strength: float = 0.0       # ADX value
    atr_14: float = 0.0
    atr_50_avg: float = 0.0
    timestamp: int = 0
@dataclass(frozen=True)
class EvidencePacket:
    """
    THE MOST VALUABLE OBJECT in the entire system.
    Immutable research data container - one per observation.
    """
    observation_id: uuid.UUID
    timestamp: int
    origin_price: float
    direction: Optional[str]  # "LONG", "SHORT", None
    book_state: BookState
    flow_state: FlowState
    liquidity_state: LiquidityState
    regime_state: RegimeState
    atr_14: float
    spread: float
    h1_conditions: Dict[str, bool]
@dataclass(frozen=True)
class OutcomeResult:
    """
    Tracks 20-minute outcome window.
    Defines the GROUND TRUTH for research.
    """
    observation_id: uuid.UUID
    tier1_reached: bool    # Price moved 1 ATR in predicted direction
    tier2_reached: bool    # Price moved 2 ATR
    tier3_reached: bool    # Price moved 3 ATR (anomaly)
    invalidated: bool      # Price returned to origin before target
    max_favorable_distance: float  # max ATR reached in correct direction
    time_to_result: int    # seconds to first tier or invalidation
    final_price: float
@dataclass(frozen=True)
class HypothesisRecord:
    """
    Hypothesis lifecycle management.
    Tracks survival criteria against immutable evidence.
    """
    id: str
    version: int
    description: str
    status: str  # "ACTIVE" / "SURVIVING" / "DEAD"
    observation_count: int
    success_count: int
    predictive_lift: float
    confidence: float
    regime_performance: Dict[str, float]  # lift by regime
    created_at: int  # timestamp
    last_evaluated: int  # timestamp
# Convenience aliases for type hints
EvidencePacketDict = Dict[str, Any]
OutcomeResultDict = Dict[str, Any]
HypothesisRecordDict = Dict[str, Any]
