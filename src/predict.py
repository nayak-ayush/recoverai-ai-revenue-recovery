import pandas as pd
import joblib
from pathlib import Path


# ==========================================
# Load trained model
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_FILE = PROJECT_ROOT / "models" / "recovery_model.pkl"

model_path = MODEL_FILE

model = joblib.load(model_path)

print("=" * 60)
print("             RECOVERAI PREDICTOR")
print("=" * 60)


# ==========================================
# Example failed payment
# ==========================================

payment = pd.DataFrame([{
    "amount": 4999,
    "payment_method": "card",
    "failure_reason": "network_timeout",
    "previous_payments": 15,
    "previous_failures": 1,
    "days_since_last_payment": 5,
    "subscription": 1,
    "hour": 14,
    "is_weekend": 0
}])


# ==========================================
# Predict probability
# ==========================================

probability = model.predict_proba(payment)[0][1]

probability_percentage = probability * 100


# ==========================================
# Determine recovery action
# ==========================================

if probability >= 0.80:

    action = "RETRY PAYMENT"
    risk = "LOW"

elif probability >= 0.60:

    action = "SCHEDULE RETRY"
    risk = "MEDIUM"

elif probability >= 0.40:

    action = "SEND PAYMENT REMINDER"
    risk = "MEDIUM"

else:

    action = "STOP AUTOMATIC RECOVERY"
    risk = "HIGH"


# ==========================================
# Display result
# ==========================================

print("\nPAYMENT DETAILS")
print("-" * 60)

print(f"Amount: ₹{payment['amount'].iloc[0]}")
print(f"Payment Method: {payment['payment_method'].iloc[0]}")
print(f"Failure Reason: {payment['failure_reason'].iloc[0]}")

print("\nAI PREDICTION")
print("-" * 60)

print(f"Recovery Probability: {probability_percentage:.2f}%")
print(f"Risk Level: {risk}")
print(f"Recommended Action: {action}")

print("\n" + "=" * 60)
print("Prediction complete!")
print("=" * 60)