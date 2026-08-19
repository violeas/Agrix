from datasets import load_dataset

print("Downloading PlantVillage dataset...")

dataset = load_dataset(
    "mohanty/PlantVillage"
)

print("\nDataset downloaded successfully!")
print(dataset)

print("\nTraining images:", len(dataset["train"]))
print("Testing images:", len(dataset["test"]))