from __future__ import annotations

from ontology.adapter.outbound.resource_adapters.sentinel_anomaly.sentinel_anomaly_adapter import (
    SentinelAnomalyAdapter,
)
from ontology.app.ports.input.anomaly_detection_use_case import AnomalyDetectionUseCase
from ontology.app.ports.output.anomaly_detection_port import AnomalyDetectionPort
from ontology.app.use_cases.anomaly_detection_interactor import AnomalyDetectionInteractor


def get_anomaly_detection_port() -> AnomalyDetectionPort:
    return SentinelAnomalyAdapter()


def get_anomaly_detection_use_case() -> AnomalyDetectionUseCase:
    return AnomalyDetectionInteractor(detector_port=get_anomaly_detection_port())
