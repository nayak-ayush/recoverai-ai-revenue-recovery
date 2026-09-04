import pandas as pd
import joblib
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report


# ==========================================
# Paths configuration
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "models"
PAYMENTS_FILE = DATA_DIR / "payments.csv"
MODEL_FILE = MODEL_DIR / "recovery_model.pkl"


# ==========================================
# 1. Load dataset
# ==========================================

df = pd.read_csv(PAYMENTS_FILE)

print("=" * 60)
print("          RECOVERAI MODEL TRAINING")
print("=" * 60)

print(f"\nTotal records: {len(df)}")


# ==========================================
# 2. Select features
# ==========================================

features = [
    "amount",
    "payment_method",
    "failure_reason",
    "previous_payments",
    "previous_failures",
    "days_since_last_payment",
    "subscription",
    "hour",
    "is_weekend"
]

target = "recovered"


X = df[features]
y = df[target]


# ==========================================
# 3. Separate categorical/numerical columns
# ==========================================

categorical_features = [
    "payment_method",
    "failure_reason"
]

numerical_features = [
    "amount",
    "previous_payments",
    "previous_failures",
    "days_since_last_payment",
    "subscription",
    "hour",
    "is_weekend"
]


# ==========================================
# 4. Preprocessing
# ==========================================

preprocessor = ColumnTransformer(
    transformers=[
        (
            "categorical",
            OneHotEncoder(handle_unknown="ignore"),
            categorical_features
        )
    ],
    remainder="passthrough"
)


# ==========================================
# 5. Create ML model
# ==========================================

model = RandomForestClassifier(
    n_estimators=200,
    random_state=42,
    class_weight="balanced"
)


# ==========================================
# 6. Create complete pipeline
# ==========================================

pipeline = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("model", model)
    ]
)


# ==========================================
# 7. Split dataset
# ==========================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)


print(f"\nTraining records: {len(X_train)}")
print(f"Testing records: {len(X_test)}")


# ==========================================
# 8. Train model
# ==========================================

print("\nTraining model...")

pipeline.fit(X_train, y_train)

print("Model training completed!")


# ==========================================
# 9. Evaluate model
# ==========================================

y_pred = pipeline.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)

print("\n" + "=" * 60)
print("MODEL PERFORMANCE")
print("=" * 60)

print(f"\nAccuracy: {accuracy * 100:.2f}%")

print("\nClassification Report:")
print(classification_report(y_test, y_pred))


# ==========================================
# 10. Save model
# ==========================================

MODEL_DIR.mkdir(parents=True, exist_ok=True)
model_path = MODEL_FILE

joblib.dump(pipeline, model_path)

print("\nModel saved successfully!")
print(f"Location: {model_path}")

print("\n" + "=" * 60)
print("Training complete!")
print("=" * 60)