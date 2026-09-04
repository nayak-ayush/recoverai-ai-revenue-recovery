import pandas as pd
import numpy as np
import random
import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PAYMENTS_FILE = DATA_DIR / "payments.csv"

# Make results reproducible
np.random.seed(42)
random.seed(42)

# Number of payment records
N = 10000

# Possible payment methods
payment_methods = [
    "card",
    "upi",
    "netbanking",
    "wallet"
]

# Possible payment failure reasons
failure_reasons = [
    "network_timeout",
    "insufficient_balance",
    "expired_card",
    "bank_decline",
    "technical_error",
    "authentication_failed"
]

records = []

# Generate payment records
for i in range(N):

    payment_id = f"PAY{i + 1:05d}"
    customer_id = f"CUST{random.randint(1, 3000):04d}"

    # Payment amount
    amount = random.randint(100, 50000)

    # Payment method
    payment_method = random.choice(payment_methods)

    # Reason for failure
    failure_reason = random.choice(failure_reasons)

    # Customer history
    previous_payments = random.randint(0, 30)
    previous_failures = random.randint(0, 8)

    # Days since customer's previous payment
    days_since_last_payment = random.randint(0, 90)

    # 1 = subscription customer, 0 = normal payment
    subscription = random.choice([0, 1])

    # Hour of payment
    hour = random.randint(0, 23)

    # 1 = weekend, 0 = weekday
    is_weekend = random.choice([0, 1])

    # ----------------------------------------
    # Create a synthetic recovery score
    # ----------------------------------------

    score = 0

    # Good payment history
    if previous_payments >= 10:
        score += 2
    elif previous_payments >= 5:
        score += 1

    # Previous failures
    if previous_failures <= 2:
        score += 2
    elif previous_failures >= 6:
        score -= 2

    # Failure type
    if failure_reason in [
        "network_timeout",
        "technical_error"
    ]:
        score += 2

    elif failure_reason == "insufficient_balance":
        score += 1

    elif failure_reason == "expired_card":
        score -= 1

    elif failure_reason == "bank_decline":
        score -= 2

    # Subscription customers
    if subscription == 1:
        score += 1

    # Convert score into probability
    probability = 0.45 + (score * 0.08)

    # Keep probability between 5% and 95%
    probability = max(0.05, min(0.95, probability))

    # Generate recovery result
    recovered = np.random.binomial(1, probability)

    records.append([
        payment_id,
        customer_id,
        amount,
        payment_method,
        failure_reason,
        previous_payments,
        previous_failures,
        days_since_last_payment,
        subscription,
        hour,
        is_weekend,
        recovered
    ])


# Column names
columns = [
    "payment_id",
    "customer_id",
    "amount",
    "payment_method",
    "failure_reason",
    "previous_payments",
    "previous_failures",
    "days_since_last_payment",
    "subscription",
    "hour",
    "is_weekend",
    "recovered"
]

# Create DataFrame
df = pd.DataFrame(records, columns=columns)

# Make sure data folder exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Save dataset
file_path = PAYMENTS_FILE

df.to_csv(file_path, index=False)

# ----------------------------------------
# Display information
# ----------------------------------------

print("=" * 50)
print("        RECOVERAI DATASET GENERATOR")
print("=" * 50)

print(f"\nDataset created successfully!")
print(f"Total records: {len(df)}")
print(f"Saved to: {file_path}")

print("\nFirst 5 records:")
print(df.head())

print("\nDataset shape:")
print(df.shape)

print("\nRecovery distribution:")
print(df["recovered"].value_counts())

print("\nRecovery percentage:")
print(df["recovered"].value_counts(normalize=True) * 100)

print("\nDataset columns:")
print(df.columns.tolist())

print("\nDone!")