# Model Weights & Serialized Artifacts

This directory stores machine learning model weights and serialized artifacts.

## Files

| File | Purpose | Size |
|:--|:--|:--|
| `yolov8n.pt` | YOLOv8-Nano detection weights | ~6.5 MB |
| `*.pkl` / `*.joblib` | Trained Isolation Forest models | Generated at runtime |

## Provenance

- **YOLOv8-Nano**: Pre-trained on COCO dataset by [Ultralytics](https://github.com/ultralytics/ultralytics). Downloaded automatically on first run.
- **Isolation Forest models**: Trained in-process during the baseline learning phase of each module. Serialized via `joblib` for session persistence.

## .gitignore

Model weights are excluded from version control (binary files, large size). They are either downloaded automatically or generated during runtime.
