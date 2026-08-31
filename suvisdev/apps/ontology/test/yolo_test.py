from pathlib import Path

import cv2
import ultralytics
from ultralytics import YOLO  # type: ignore[attr-defined]


def main() -> None:
    model = YOLO("yolo11n.pt")
    image_path = Path(ultralytics.__file__).parent / "assets" / "bus.jpg"

    results = model(str(image_path))
    annotated = results[0].plot()

    cv2.imshow("YOLO Hello World", annotated)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
