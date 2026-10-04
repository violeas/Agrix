import math
import os
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError

from services.recommendations import knowledge_for, unsupported_crop_response


try:
    import torch
    import torch.nn as nn
    from torchvision import models, transforms
except Exception:  # pragma: no cover - handled at runtime for friendly errors
    torch = None
    nn = None
    models = None
    transforms = None


BASE_DIR = Path(__file__).resolve().parent.parent
DISEASE_MODEL_PATH = Path(os.getenv("DISEASE_MODEL_PATH", BASE_DIR / "model" / "disease_model.pth"))

CROP_ALIASES = {
    "corn": "Maize",
    "corn maize": "Maize",
    "maize": "Maize",
    "pepper bell": "Bell Pepper",
    "bell pepper": "Bell Pepper",
    "cherry including sour": "Cherry",
}


def _device():
    if torch is None:
        return None
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def normalize_text(value):
    return " ".join(
        str(value or "")
        .replace("Corn_(maize)", "Maize")
        .replace("Pepper,_bell", "Bell Pepper")
        .replace("Cherry_(including_sour)", "Cherry")
        .replace("(", " ")
        .replace(")", " ")
        .replace(",", " ")
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )


def canonical_crop_name(value):
    normalized = normalize_text(value)
    key = normalized.lower()
    return CROP_ALIASES.get(key, normalized.title() if normalized else "")


def parse_plantvillage_label(label):
    if "___" not in label:
        crop = canonical_crop_name(label)
        return {
            "crop": crop,
            "disease": "",
            "is_healthy": False,
            "raw_label": label,
        }

    raw_crop, raw_disease = label.split("___", 1)
    crop = canonical_crop_name(raw_crop)
    disease = normalize_text(raw_disease)
    is_healthy = disease.lower() == "healthy"

    return {
        "crop": crop,
        "disease": "Healthy" if is_healthy else disease,
        "is_healthy": is_healthy,
        "raw_label": label,
    }


def _same_crop(left, right):
    return canonical_crop_name(left).lower() == canonical_crop_name(right).lower()


def _confidence_label(probability, crop_probability, margin, quality_ok):
    if not quality_ok:
        return "Low"
    if probability >= 0.62 and crop_probability >= 0.55 and margin >= 0.18:
        return "High"
    if probability >= 0.34 and crop_probability >= 0.34 and margin >= 0.08:
        return "Moderate"
    return "Low"


def _health_score(diagnosis, reliability, confidence):
    if diagnosis == "Healthy":
        return 92 if reliability == "High" else 84
    if reliability == "High":
        return 62
    if reliability == "Moderate":
        return 72
    if confidence is None:
        return None
    return 78


def _health_status(diagnosis, reliability, status):
    if status == "inconclusive":
        return "Needs clearer evidence"
    if diagnosis == "Healthy":
        return "Good"
    if reliability == "High":
        return "Concern"
    if reliability == "Moderate":
        return "Watch"
    return "Needs clearer evidence"


def _description_alignment(description, knowledge):
    text = (description or "").strip().lower()
    if not text:
        return "No farmer observation was provided."
    hints = " ".join(knowledge.get("symptoms", []) + knowledge.get("visual_indicators", [])).lower()
    words = [word for word in text.replace(",", " ").replace(".", " ").split() if len(word) > 4]
    matches = [word for word in words if word in hints]
    if matches:
        return "The farmer observation supports the crop-specific visual assessment."
    return "The farmer observation was saved, but it does not fully confirm the visual model result. A clearer image or expert confirmation is recommended."


def _quality_report(image):
    width, height = image.size
    grayscale = image.convert("L")
    stat = ImageStat.Stat(grayscale)
    brightness = stat.mean[0]
    contrast = math.sqrt(stat.var[0]) if stat.var else 0
    edges = ImageStat.Stat(grayscale.filter(ImageFilter.FIND_EDGES)).mean[0]

    issues = []
    if width < 160 or height < 160:
        issues.append("Image is too small for reliable leaf or symptom analysis.")
    if brightness < 28:
        issues.append("Image is too dark for reliable diagnosis.")
    if brightness > 235:
        issues.append("Image is overexposed for reliable diagnosis.")
    if contrast < 16 and edges < 6:
        issues.append("Image lacks enough visible detail for reliable diagnosis.")

    return {
        "width": width,
        "height": height,
        "brightness": round(brightness, 1),
        "contrast": round(contrast, 1),
        "quality_ok": not issues,
        "issues": issues,
    }


class DiseaseAnalyzer:
    def __init__(self):
        self._model = None
        self._classes = None
        self._parsed_classes = None
        self._model_error = ""

    def _load(self):
        if self._model is not None:
            return self._model, self._classes
        if self._model_error:
            raise RuntimeError(self._model_error)
        if torch is None or models is None or transforms is None:
            self._model_error = "PyTorch or torchvision is not installed in this Python environment."
            raise RuntimeError(self._model_error)
        if not DISEASE_MODEL_PATH.exists():
            self._model_error = (
                "Disease model not found. Train it with python train_disease_model.py, "
                "or set DISEASE_MODEL_PATH."
            )
            raise RuntimeError(self._model_error)

        device = _device()
        checkpoint = torch.load(DISEASE_MODEL_PATH, map_location=device)
        classes = checkpoint.get("disease_classes") or checkpoint.get("classes")
        if not classes:
            self._model_error = "Disease model checkpoint does not include disease_classes."
            raise RuntimeError(self._model_error)

        model = models.mobilenet_v3_small(weights=None)
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, len(classes))
        model.load_state_dict(checkpoint["model_state_dict"])
        model = model.to(device)
        model.eval()

        self._model = model
        self._classes = classes
        self._parsed_classes = [parse_plantvillage_label(label) for label in classes]
        return self._model, self._classes

    def supported_crops(self):
        try:
            self._load()
        except RuntimeError:
            return ["Tomato", "Maize", "Potato", "Rose"]
        crops = sorted({item["crop"] for item in self._parsed_classes if item["crop"]})
        if "Rose" not in crops:
            crops.append("Rose")
        return crops

    def _predict_probabilities(self, image):
        model, classes = self._load()
        device = _device()
        transform = transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )
        tensor = transform(image.convert("RGB")).unsqueeze(0).to(device)
        with torch.no_grad():
            output = model(tensor)
            probabilities = torch.softmax(output, dim=1).squeeze(0).detach().cpu().tolist()
        return list(zip(classes, probabilities))

    def analyze(self, image_path, crop_name, description=""):
        selected_crop = canonical_crop_name(crop_name)
        if not selected_crop:
            return _inconclusive_response(
                "Unknown crop",
                ["The crop was not provided, so crop-specific disease filtering could not be applied."],
                "Please enter the crop or plant name before analyzing.",
            )

        try:
            image = Image.open(image_path).convert("RGB")
        except (FileNotFoundError, UnidentifiedImageError, OSError):
            return _inconclusive_response(
                selected_crop,
                ["The uploaded file could not be opened as a crop image."],
                "Please upload a clear JPG or PNG image.",
            )

        quality = _quality_report(image)

        try:
            predictions = self._predict_probabilities(image)
        except RuntimeError as error:
            response = _inconclusive_response(
                selected_crop,
                ["The disease model is not available in this Python environment."],
                str(error),
            )
            response["model_note"] = str(error)
            return response

        parsed_predictions = [
            {
                **parse_plantvillage_label(label),
                "probability": probability,
            }
            for label, probability in predictions
        ]
        top_predictions = [
            {
                "crop": item["crop"],
                "disease": item["disease"] or item["raw_label"],
                "label": item["raw_label"],
                "confidence": round(item["probability"] * 100, 1),
            }
            for item in sorted(parsed_predictions, key=lambda item: item["probability"], reverse=True)[:3]
        ]
        relevant = [item for item in parsed_predictions if _same_crop(item["crop"], selected_crop)]

        if not relevant:
            response = unsupported_crop_response(selected_crop)
            response["top_predictions"] = top_predictions
            return response

        relevant.sort(key=lambda item: item["probability"], reverse=True)
        global_best = max(parsed_predictions, key=lambda item: item["probability"])
        top = relevant[0]
        second = relevant[1]["probability"] if len(relevant) > 1 else 0
        crop_probability = sum(item["probability"] for item in relevant)
        margin = top["probability"] - second
        model_confidence = round(top["probability"] * 100, 1)
        reliability = _confidence_label(top["probability"], crop_probability, margin, quality["quality_ok"])

        if not _same_crop(global_best["crop"], selected_crop) and global_best["probability"] >= 0.4:
            return _inconclusive_response(
                selected_crop,
                [
                    f"Farmer selected crop: {selected_crop}.",
                    "The visual model produced a stronger result for a different crop, so AgriShield did not use it as the diagnosis.",
                    "Please upload a clearer close-up of the affected plant part.",
                ],
                "Upload a closer image of the affected leaf or plant part for a reliable crop-specific diagnosis.",
                model_confidence=model_confidence,
                model_label=top["raw_label"],
                top_predictions=top_predictions,
            )

        weak_crop_match = crop_probability < 0.18
        weak_prediction = top["probability"] < 0.12 or reliability == "Low"
        if quality["issues"] or weak_crop_match or weak_prediction:
            reasons = [
                f"Farmer selected crop: {selected_crop}; model search was restricted to {selected_crop} classes.",
                f"Best crop-specific model match: {top['disease'] or top['raw_label']} ({model_confidence}%).",
            ]
            if not _same_crop(global_best["crop"], selected_crop):
                reasons.append(
                    "The model's strongest overall signal belonged to a different crop, so it was not used as the diagnosis."
                )
            reasons.extend(quality["issues"])
            if description.strip():
                reasons.append(f"Farmer observation: {description.strip()}")
            return _inconclusive_response(
                selected_crop,
                reasons,
                "Please upload a closer image of the affected leaf or plant part.",
                model_confidence=model_confidence,
                model_label=top["raw_label"],
                top_predictions=top_predictions,
            )

        is_healthy = top["is_healthy"]
        diagnosis = "Healthy" if is_healthy else top["disease"]
        knowledge = knowledge_for(selected_crop, diagnosis, is_healthy=is_healthy)
        status = "not_applicable" if is_healthy else "suspected"
        severity = "None" if is_healthy else "Unknown"
        health_score = _health_score(diagnosis, reliability, model_confidence)
        evidence = [
            f"Farmer selected crop: {selected_crop}; unrelated crop classes were excluded.",
            f"Best crop-specific model match: {diagnosis} ({model_confidence}%).",
            "Image has enough size and contrast for model input.",
        ]
        if description.strip():
            evidence.append(f"Farmer observation: {description.strip()}")
        if not is_healthy:
            evidence.append("The current classifier identifies disease class, but it does not measure lesion area or severity grade.")

        return {
            "crop_name": selected_crop,
            "diagnosis": diagnosis,
            "diagnosis_status": status,
            "reliability": reliability,
            "model_confidence": model_confidence,
            "severity": severity,
            "health_status": _health_status(diagnosis, reliability, status),
            "health_score": health_score,
            "evidence": evidence,
            "possible_causes": knowledge["possible_causes"],
            "recommendations": knowledge["recommendations"],
            "visual_indicators": knowledge["visual_indicators"],
            "preventive_measures": knowledge["preventive_measures"],
            "medicine_guidance": knowledge["medicine_guidance"],
            "fertilizer_guidance": knowledge["fertilizer_guidance"],
            "natural_remedies": knowledge["natural_remedies"],
            "expert_confirmation": knowledge["expert_confirmation"],
            "description_alignment": _description_alignment(description, knowledge),
            "top_predictions": top_predictions,
            "precautions": knowledge["precautions"],
            "do_not": knowledge["do_not"],
            "next_check": knowledge["next_check"],
            "follow_up": knowledge["follow_up"],
            "model_label": top["raw_label"],
            "model_note": (
                "Severity is marked Unknown because the trained PlantVillage classifier "
                "does not estimate severity from lesion extent."
            ),
        }


def _inconclusive_response(crop_name, evidence, follow_up, model_confidence=None, model_label="", top_predictions=None):
    return {
        "crop_name": crop_name,
        "diagnosis": "Insufficient visual evidence",
        "diagnosis_status": "inconclusive",
        "reliability": "Low",
        "model_confidence": model_confidence,
        "severity": "Unknown",
        "health_status": "Needs clearer evidence",
        "health_score": None,
        "evidence": evidence,
        "possible_causes": [
            "Disease, pest damage, nutrient stress, water stress, or physical injury could still be possible.",
        ],
        "recommendations": [
            "Upload a closer image of the affected leaf or plant part.",
            "Capture the image in natural light and keep the affected area in focus.",
            "Check nearby plants before taking action.",
        ],
        "visual_indicators": [],
        "preventive_measures": [
            "Keep the field clean while monitoring symptoms.",
            "Avoid unnecessary leaf wetness.",
            "Record whether symptoms spread to nearby plants.",
        ],
        "medicine_guidance": [
            "No medicine is suggested from an uncertain diagnosis.",
            "Use chemical treatment only after a clearer scan or local expert confirmation.",
        ],
        "fertilizer_guidance": [
            "Do not apply fertilizer as a disease treatment from this uncertain result.",
            "Use fertilizer only if separate nutrient-deficiency evidence supports it.",
        ],
        "natural_remedies": [
            "Remove only clearly dead or badly damaged tissue.",
            "Improve airflow and water at soil level.",
            "Rescan with a close-up image before escalating treatment.",
        ],
        "expert_confirmation": "Recommended if symptoms are spreading, severe, or treatment decisions are urgent.",
        "description_alignment": "The farmer observation was saved, but visual evidence is insufficient for reliable confirmation.",
        "top_predictions": top_predictions or [],
        "precautions": [
            "Keep the crop under observation until the next scan.",
            "Use clean tools if removing visibly damaged tissue.",
        ],
        "do_not": [
            "Do not treat this as a confirmed disease.",
            "Do not apply pesticide or fertilizer only from this uncertain result.",
        ],
        "next_check": [
            "Photograph the affected area close up.",
            "Photograph a healthy nearby leaf for comparison.",
            "Add notes about recent rain, irrigation, pests, and how fast symptoms are spreading.",
        ],
        "follow_up": follow_up,
        "model_label": model_label,
        "model_note": "Insufficient visual evidence for a reliable diagnosis.",
    }


@lru_cache(maxsize=1)
def get_analyzer():
    return DiseaseAnalyzer()
