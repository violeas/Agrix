import os

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms


CROP_MODEL_PATH = "model/crop_model.pth"
DISEASE_MODEL_PATH = os.getenv(
    "DISEASE_MODEL_PATH",
    "model/disease_model.pth"
)

device = torch.device(
    "mps" if torch.backends.mps.is_available() else "cpu"
)

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


def _load_mobilenet_checkpoint(model_path, class_key):
    checkpoint = torch.load(
        model_path,
        map_location=device
    )

    classes = checkpoint.get(class_key) or checkpoint.get("classes")

    if not classes:
        raise ValueError(
            f"Checkpoint {model_path} does not contain '{class_key}'."
        )

    classifier = models.mobilenet_v3_small(weights=None)

    classifier.classifier[3] = nn.Linear(
        classifier.classifier[3].in_features,
        len(classes)
    )

    classifier.load_state_dict(checkpoint["model_state_dict"])
    classifier = classifier.to(device)
    classifier.eval()

    return classifier, classes


crop_model, crop_classes = _load_mobilenet_checkpoint(
    CROP_MODEL_PATH,
    "crop_classes"
)

disease_model = None
disease_classes = None


def _prepare_image(image):
    if not isinstance(image, Image.Image):
        image = Image.open(image)

    image = image.convert("RGB")

    tensor = transform(image)
    return tensor.unsqueeze(0).to(device)


def _predict(model, classes, image):
    tensor = _prepare_image(image)

    with torch.no_grad():
        output = model(tensor)
        probabilities = torch.softmax(output, dim=1)
        confidence, prediction = torch.max(
            probabilities,
            dim=1
        )

    label = classes[prediction.item()]
    confidence = confidence.item() * 100

    return label, confidence


def parse_plantvillage_label(label):
    """Convert PlantVillage labels into crop and disease fields."""
    if "___" not in label:
        return {
            "crop": label,
            "disease": "",
            "is_healthy": False,
            "raw_label": label
        }

    crop, disease = label.split("___", 1)

    crop = (
        crop
        .replace("Corn_(maize)", "Maize")
        .replace("Pepper,_bell", "Bell Pepper")
        .replace("Cherry_(including_sour)", "Cherry")
        .replace("_", " ")
    )

    disease = disease.replace("_", " ").strip()
    is_healthy = disease.lower() == "healthy"

    return {
        "crop": crop,
        "disease": "Healthy" if is_healthy else disease,
        "is_healthy": is_healthy,
        "raw_label": label
    }


def predict_crop(image):
    """Backward-compatible crop-only prediction."""
    return _predict(crop_model, crop_classes, image)


def _get_disease_model():
    global disease_model, disease_classes

    if disease_model is not None and disease_classes is not None:
        return disease_model, disease_classes

    if not os.path.exists(DISEASE_MODEL_PATH):
        raise FileNotFoundError(
            "Disease model not found. Train it with: "
            "python train_disease_model.py. "
            "The current crop_model.pth has only 14 crop classes, "
            "so it cannot detect crop diseases."
        )

    disease_model, disease_classes = _load_mobilenet_checkpoint(
        DISEASE_MODEL_PATH,
        "disease_classes"
    )

    return disease_model, disease_classes


def predict_crop_disease(image):
    """Predict both crop and disease using the 38-class disease model."""
    classifier, classes = _get_disease_model()
    label, confidence = _predict(classifier, classes, image)
    parsed = parse_plantvillage_label(label)

    return {
        **parsed,
        "confidence": confidence
    }
