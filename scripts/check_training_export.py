"""One-epoch synthetic training -> saved checkpoint -> ONNX CPU inference smoke test."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new directory for disposable smoke data")
    args = parser.parse_args()
    root = args.output.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=False)
    config_dir = root / "yolo-config"
    config_dir.mkdir()
    os.environ["YOLO_CONFIG_DIR"] = str(config_dir)
    os.environ["YOLO_OFFLINE"] = "true"
    os.environ["YOLO_AUTOINSTALL"] = "false"
    os.environ["WANDB_MODE"] = "disabled"
    import cv2
    import matplotlib
    import numpy as np
    import onnx
    import onnxruntime as ort
    import torch
    import yaml
    from ultralytics import YOLO
    from ultralytics.utils import USER_CONFIG_DIR, SETTINGS
    from citrus_vision.config import ModelConfig
    from citrus_vision.inference import create_detector

    SETTINGS.update({key: False for key in ("wandb", "mlflow", "comet", "clearml", "neptune",
                                            "tensorboard", "dvc", "raytune") if key in SETTINGS})
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf", USER_CONFIG_DIR / "Arial.ttf")
    for split in ("train", "val"):
        (root / "data/images" / split).mkdir(parents=True)
        (root / "data/labels" / split).mkdir(parents=True)
        for index in range(2):
            frame = np.zeros((64, 64, 3), dtype=np.uint8)
            cv2.rectangle(frame, (16, 16), (48, 48), (0, 255, 0), -1)
            assert cv2.imwrite(str(root / f"data/images/{split}/{index}.jpg"), frame)
            (root / f"data/labels/{split}/{index}.txt").write_text("0 0.5 0.5 0.5 0.5\n")
    YOLO("yolo11n.yaml", task="detect").save(root / "initial.pt")
    dataset = root / "dataset.yaml"
    dataset.write_text(yaml.safe_dump(dict(path=str(root / "data"), train="images/train",
                                          val="images/val", names={0: "synthetic_square"})))
    config = root / "train.yaml"
    config.write_text(yaml.safe_dump(dict(model=str(root / "initial.pt"), data=str(dataset),
                                          name="smoke", epochs=1, imgsz=64, device="cpu", batch=2,
                                          workers=0, amp=False, plots=False, mosaic=0., pretrained=False)))
    project = root / "runs"
    subprocess.run([sys.executable, "-c", "from citrus_vision.cli import train_main; train_main()",
                    "--config", str(config), "--project", str(project)], check=True)
    checkpoint = project / "smoke/weights/best.pt"
    assert checkpoint.is_file(), "Trainer did not save best.pt"
    image = cv2.imread(str(root / "data/images/val/0.jpg"))
    model = YOLO(str(checkpoint), task="detect")
    assert len(model.predict(image, imgsz=64, device="cpu", verbose=False)) == 1
    subprocess.run([sys.executable, "-c", "from citrus_vision.cli import export_main; export_main()",
                    "--weights", str(checkpoint), "--format", "onnx", "--imgsz", "64"], check=True)
    exported = checkpoint.with_suffix(".onnx")
    onnx.checker.check_model(str(exported))
    session = ort.InferenceSession(str(exported), providers=["CPUExecutionProvider"])
    outputs = session.run(None, {session.get_inputs()[0].name: np.zeros((1, 3, 64, 64), np.float32)})
    assert outputs and all(np.isfinite(output).all() for output in outputs)
    with torch.no_grad():
        reference = model.model(torch.zeros((1, 3, 64, 64)))
    if isinstance(reference, (list, tuple)):
        reference = reference[0]
    np.testing.assert_allclose(outputs[0], reference.cpu().numpy(), rtol=1e-3, atol=1e-3)
    detector = create_detector(ModelConfig(path=str(exported), image_size=64), root)
    detector.detect(image)
    result = {"synthetic": True, "epochs": 1, "checkpoint": str(checkpoint),
              "onnx": str(exported), "onnx_shapes": [list(output.shape) for output in outputs],
              "onnx_matches_pytorch": True, "shared_detector_onnx": True}
    (root / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
