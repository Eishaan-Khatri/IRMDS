"""
Pydantic schemas for the Network Traffic module.

Ensures absolute data integrity across the boundaries of the generator,
extractor, and ML components.
"""

from typing import Literal

from pydantic import BaseModel, Field


class PacketConfig(BaseModel):
    """Immutable representation of a single network packet."""

    timestamp: float
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: Literal["TCP", "UDP", "ICMP"]
    size_bytes: int = Field(..., ge=0, le=9000)  # Max Jumbo frame


class FeatureWindow(BaseModel):
    """Extracted network baseline features over a discrete time window."""

    start_time: float
    end_time: float
    packets_per_second: float = Field(..., ge=0)
    bytes_per_second: float = Field(..., ge=0)
    unique_src_ips: int = Field(..., ge=0)
    unique_dst_ports: int = Field(..., ge=0)
    tcp_ratio: float = Field(..., ge=0.0, le=1.0)
    udp_ratio: float = Field(..., ge=0.0, le=1.0)
    icmp_ratio: float = Field(..., ge=0.0, le=1.0)
    dst_ip_entropy: float = Field(..., ge=0.0)
    avg_packet_size: float = Field(..., ge=0.0)
    max_packet_size: int = Field(..., ge=0)


class NetworkAnomalyResult(BaseModel):
    """The final ML decision for a given feature window."""

    is_anomaly: bool
    anomaly_type: str | None = None
    isolation_forest_score: float
    z_scores: dict[str, float]
    triggers: list[str] = Field(default_factory=list)
