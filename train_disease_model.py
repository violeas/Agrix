import os

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, models, transforms


# -----------------------------
# SETTINGS
# -----------------------------
DATA_DIR = "data/PlantVillage/raw/color"
MODEL_DIR = "model"
MODEL_PATH = os.path.join(MODEL_DIR, "disease_model.pth")

BATCH_SIZE = 32
EPOCHS = 8
IMAGE_SIZE = 224
SEED = 42

os.makedirs(MODEL_DIR, exist_ok=True)


# -----------------------------
# DEVICE
# -----------------------------
if torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
elif torch.cuda.is_available():
    DEVICE = torch.device("cuda")
else:
    DEVICE = torch.device("cpu")

print("Using device:", DEVICE)


# -----------------------------
# DATASET
# -----------------------------
train_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(12),
    transforms.ColorJitter(
        brightness=0.12,
        contrast=0.12,
        saturation=0.08
    ),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

eval_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

base_dataset = datasets.ImageFolder(
    DATA_DIR,
    transform=None
)

disease_classes = base_dataset.classes

print("\nDisease classes:")
for index, class_name in enumerate(disease_classes):
    print(index, class_name)

total = len(base_dataset)
train_size = int(0.8 * total)
val_size = int(0.1 * total)
test_size = total - train_size - val_size

generator = torch.Generator().manual_seed(SEED)
indices = torch.randperm(total, generator=generator).tolist()

train_indices = indices[:train_size]
val_indices = indices[train_size:train_size + val_size]
test_indices = indices[train_size + val_size:]

train_source = datasets.ImageFolder(
    DATA_DIR,
    transform=train_transform
)
eval_source = datasets.ImageFolder(
    DATA_DIR,
    transform=eval_transform
)

train_dataset = Subset(train_source, train_indices)
val_dataset = Subset(eval_source, val_indices)
test_dataset = Subset(eval_source, test_indices)

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
print("\nLoading MobileNetV3 disease classifier...")

weights = models.MobileNet_V3_Small_Weights.DEFAULT
model = models.mobilenet_v3_small(weights=weights)

model.classifier[3] = nn.Linear(
    model.classifier[3].in_features,
    len(disease_classes)
)

model = model.to(DEVICE)

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=0.0001,
    weight_decay=0.01
)


def evaluate(loader):
    model.eval()
    correct = 0
    total_seen = 0

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(DEVICE)
            labels = labels.to(DEVICE)
            outputs = model(images)
            predictions = outputs.argmax(dim=1)
            correct += (predictions == labels).sum().item()
            total_seen += labels.size(0)

    return 100 * correct / max(total_seen, 1)


# -----------------------------
# TRAINING
# -----------------------------
print("\nStarting disease training...\n")

best_val_accuracy = 0

for epoch in range(EPOCHS):
    model.train()
    correct = 0
    total_seen = 0
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
        total_seen += labels.size(0)

    train_accuracy = 100 * correct / max(total_seen, 1)
    val_accuracy = evaluate(val_loader)

    print(
        f"Epoch {epoch + 1}/{EPOCHS} | "
        f"Loss: {running_loss / len(train_loader):.4f} | "
        f"Train: {train_accuracy:.2f}% | "
        f"Val: {val_accuracy:.2f}%"
    )

    if val_accuracy > best_val_accuracy:
        best_val_accuracy = val_accuracy
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "disease_classes": disease_classes
            },
            MODEL_PATH
        )
        print("Saved best disease model.")


# -----------------------------
# TEST
# -----------------------------
print("\nTesting best disease model...")

checkpoint = torch.load(
    MODEL_PATH,
    map_location=DEVICE
)
model.load_state_dict(checkpoint["model_state_dict"])

test_accuracy = evaluate(test_loader)
print(f"\nTest Accuracy: {test_accuracy:.2f}%")
print("\nDisease model saved to:")
print(MODEL_PATH)
