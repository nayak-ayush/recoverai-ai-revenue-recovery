import pandas as pd
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAYMENTS_FILE = PROJECT_ROOT / "data" / "payments.csv"

# Load dataset
df = pd.read_csv(PAYMENTS_FILE)

print("=" * 60)
print("             RECOVERAI DATA ANALYSIS")
print("=" * 60)

# 1. Dataset size
print("\n1. DATASET SIZE")
print("-" * 60)
print(f"Rows: {df.shape[0]}")
print(f"Columns: {df.shape[1]}")

# 2. Column names
print("\n2. COLUMNS")
print("-" * 60)

for column in df.columns:
    print(column)

# 3. Data types
print("\n3. DATA TYPES")
print("-" * 60)
print(df.dtypes)

# 4. Missing values
print("\n4. MISSING VALUES")
print("-" * 60)
print(df.isnull().sum())

# 5. Duplicate records
print("\n5. DUPLICATE RECORDS")
print("-" * 60)
print(df.duplicated().sum())

# 6. Payment statistics
print("\n6. PAYMENT AMOUNT STATISTICS")
print("-" * 60)
print(df["amount"].describe())

# 7. Payment methods
print("\n7. PAYMENT METHODS")
print("-" * 60)
print(df["payment_method"].value_counts())

# 8. Failure reasons
print("\n8. FAILURE REASONS")
print("-" * 60)
print(df["failure_reason"].value_counts())

# 9. Recovery distribution
print("\n9. RECOVERY DISTRIBUTION")
print("-" * 60)
print(df["recovered"].value_counts())

# 10. Recovery percentage
print("\n10. RECOVERY PERCENTAGE")
print("-" * 60)

recovery_percentage = df["recovered"].mean() * 100

print(f"Overall recovery rate: {recovery_percentage:.2f}%")

# 11. Average payment amount
print("\n11. AVERAGE PAYMENT")
print("-" * 60)

print(f"Average payment: ₹{df['amount'].mean():.2f}")

# 12. Revenue at risk
print("\n12. REVENUE AT RISK")
print("-" * 60)

total_revenue = df["amount"].sum()
recovered_revenue = df.loc[df["recovered"] == 1, "amount"].sum()
lost_revenue = df.loc[df["recovered"] == 0, "amount"].sum()

print(f"Total payment value: ₹{total_revenue:,.2f}")
print(f"Recovered revenue: ₹{recovered_revenue:,.2f}")
print(f"Unrecovered revenue: ₹{lost_revenue:,.2f}")

# 13. Recovery by failure reason
print("\n13. RECOVERY RATE BY FAILURE REASON")
print("-" * 60)

recovery_by_reason = (
    df.groupby("failure_reason")["recovered"]
    .mean()
    .sort_values(ascending=False)
    * 100
)

print(recovery_by_reason)

# 14. Recovery by payment method
print("\n14. RECOVERY RATE BY PAYMENT METHOD")
print("-" * 60)

recovery_by_method = (
    df.groupby("payment_method")["recovered"]
    .mean()
    .sort_values(ascending=False)
    * 100
)

print(recovery_by_method)

print("\n" + "=" * 60)
print("Analysis complete!")
print("=" * 60)