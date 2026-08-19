import os
import random
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms, models

# -----------------------------
# SETTINGS
# -----------------------------
DATA_DIR = "data/PlantVillage/raw/color"
MODEL_DIR = "model"

BATCH_SIZE = 32
EPOCHS = 5
IMAGE_SIZE = 224

os.makedirs(MODEL_DIR, exist_ok=True)

# -----------------------------
# DEVICE
# -----------------------------
if torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
else:
    DEVICE = torch.device("cpu")

print("Using device:", DEVICE)

# -----------------------------
# LOAD DATASET
# -----------------------------
transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

dataset = datasets.ImageFolder(
    DATA_DIR,
    transform=transform
)

# -----------------------------
# CONVERT 38 DISEASE CLASSES
# INTO 14 CROP CLASSES
# -----------------------------
crop_names = []

for class_name in dataset.classes:
    crop = class_name.split("___")[0]

    if crop == "Corn_(maize)":
        crop = "Maize"
    elif crop == "Pepper,_bell":
        crop = "Bell Pepper"
    elif crop == "Cherry_(including_sour)":
        crop = "Cherry"

    crop_names.append(crop)

crop_classes = sorted(set(crop_names))

print("\nCrop classes:")
for i, crop in enumerate(crop_classes):
    print(i, crop)

# Map original disease class → crop class
original_to_crop = {
    i: crop_classes.index(crop_names[i])
    for i in range(len(dataset.classes))
}

# -----------------------------
# CREATE CROP DATASET
# -----------------------------
class CropDataset(torch.utils.data.Dataset):

    def __init__(self, image_dataset, mapping):
        self.dataset = image_dataset
        self.mapping = mapping

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, index):
        image, original_label = self.dataset[index]
        crop_label = self.mapping[original_label]
        return image, crop_label


crop_dataset = CropDataset(dataset, original_to_crop)

# -----------------------------
# SPLIT DATA
# -----------------------------
total = len(crop_dataset)

train_size = int(0.8 * total)
val_size = int(0.1 * total)
test_size = total - train_size - val_size

generator = torch.Generator().manual_seed(42)

train_dataset, val_dataset, test_dataset = random_split(
    crop_dataset,
    [train_size, val_size, test_size],
    generator=generator
)

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=0
)

val_loader = DataLoader(
    val_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0
)

test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0
)

print("\nImages:")
print("Training:", len(train_dataset))
print("Validation:", len(val_dataset))
print("Testing:", len(test_dataset))

# -----------------------------
# MODEL
# -----------------------------
print("\nLoading MobileNetV3...")

weights = models.MobileNet_V3_Small_Weights.DEFAULT

model = models.mobilenet_v3_small(
    weights=weights
)

# Replace classifier
model.classifier[3] = nn.Linear(
    model.classifier[3].in_features,
    len(crop_classes)
)

model = model.to(DEVICE)

# -----------------------------
# LOSS + OPTIMIZER
# -----------------------------
criterion = nn.CrossEntropyLoss()

optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=0.0001
)

# -----------------------------
# TRAINING
# -----------------------------
print("\nStarting training...\n")

for epoch in range(EPOCHS):

    model.train()

    correct = 0
    total_train = 0
    running_loss = 0

    for images, labels in train_loader:

        images = images.to(DEVICE)
        labels = labels.to(DEVICE)

        optimizer.zero_grad()

        outputs = model(images)

        loss = criterion(outputs, labels)

        loss.backward()

        optimizer.step()

        running_loss += loss.item()

        predictions = outputs.argmax(dim=1)

        correct += (predictions == labels).sum().item()
        total_train += labels.size(0)

    train_accuracy = 100 * correct / total_train

    # -------------------------
    # VALIDATION
    # -------------------------

    model.eval()

    correct = 0
    total_val = 0

    with torch.no_grad():

        for images, labels in val_loader:

            images = images.to(DEVICE)
            labels = labels.to(DEVICE)

            outputs = model(images)

            predictions = outputs.argmax(dim=1)

            correct += (predictions == labels).sum().item()
            total_val += labels.size(0)

    val_accuracy = 100 * correct / total_val

    print(
        f"Epoch {epoch + 1}/{EPOCHS} | "
        f"Loss: {running_loss / len(train_loader):.4f} | "
        f"Train: {train_accuracy:.2f}% | "
        f"Val: {val_accuracy:.2f}%"
    )

# -----------------------------
# TEST
# -----------------------------
print("\nTesting model...")

model.eval()

correct = 0
total = 0

with torch.no_grad():

    for images, labels in test_loader:

        images = images.to(DEVICE)
        labels = labels.to(DEVICE)

        outputs = model(images)

        predictions = outputs.argmax(dim=1)

        correct += (predictions == labels).sum().item()
        total += labels.size(0)

test_accuracy = 100 * correct / total

print(f"\nTest Accuracy: {test_accuracy:.2f}%")

# -----------------------------
# SAVE MODEL
# -----------------------------

model_path = os.path.join(
    MODEL_DIR,
    "crop_model.pth"
)

torch.save(
    {
        "model_state_dict": model.state_dict(),
        "crop_classes": crop_classes
    },
    model_path
)

print("\nModel saved to:")
print(model_path)