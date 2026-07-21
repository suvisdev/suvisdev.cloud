from pathlib import Path

from ontology.adapter.outbound.resource_adapters.convnext.timm_convnext_adapter import (
    TimmConvnextAdapter,
)
from ontology.app.ports.input.image_classifier_use_case import ImageClassifierUseCase
from ontology.app.ports.output.image_classifier_port import ImageClassifierPort
from ontology.app.use_cases.image_classifier_interactor import ImageClassifierInteractor

_RUNS_DIR = Path(__file__).resolve().parent.parent / "runs" / "genre_classify"
_WEIGHTS_PATH = _RUNS_DIR / "weights" / "best.pth"
_CLASSES_PATH = _RUNS_DIR / "classes.json"


def get_image_classifier_port() -> ImageClassifierPort:
    return TimmConvnextAdapter(weights_path=_WEIGHTS_PATH, classes_path=_CLASSES_PATH)


def get_image_classifier_use_case() -> ImageClassifierUseCase:
    return ImageClassifierInteractor(classifier_port=get_image_classifier_port())
