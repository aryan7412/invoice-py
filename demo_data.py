import numpy as np
import pandas as pd


def make_demo_data(historical_rows=650, current_rows=40, seed=42):
    rng = np.random.default_rng(seed)
    customers = [f"Customer {c}" for c in "ABCDEFGHIJKLMNO"]
    regions = ["North","South","East","West"]
    total = historical_rows + current_rows

    customer = rng.choice(customers, total)
    invoice_amount = rng.integers(15000, 250000, total).astype(float)
    avg_payment_days = rng.integers(15, 75, total)
    previous_late = rng.integers(0, 7, total)
    credit_period = rng.choice([15,30,45,60], total)
    region = rng.choice(regions, total)

    score = (
        -2.2
        + 0.035*(avg_payment_days-30)
        + 0.34*previous_late
        + 0.018*(credit_period-30)
        + 0.000003*invoice_amount
    )
    probability = 1/(1+np.exp(-score))
    paid_late = (rng.random(total) < probability).astype(int)

    dates = pd.Timestamp("2025-01-01") + pd.to_timedelta(
        rng.integers(0,600,total), unit="D"
    )

    df = pd.DataFrame({
        "Customer": customer,
        "Invoice ID": [f"INV-{i:04d}" for i in range(1,total+1)],
        "Invoice Date": dates,
        "Invoice Amount": invoice_amount,
        "Average Payment Days": avg_payment_days,
        "Previous Late Payments": previous_late,
        "Credit Period Days": credit_period,
        "Outstanding Amount": invoice_amount,
        "Region": region,
        "Paid Late": paid_late,
    })

    current = df.index >= historical_rows
    df.loc[current, "Paid Late"] = np.nan
    df.loc[current, "Outstanding Amount"] = (
        df.loc[current, "Invoice Amount"]
        * rng.choice([0.35,0.5,0.75,1.0], current.sum())
    ).round(0)
    df.loc[current, "Invoice Date"] = (
        pd.Timestamp("2026-08-01")
        + pd.to_timedelta(
            rng.integers(0,65,current.sum()), unit="D"
        )
    )

    return df


if __name__ == "__main__":
    data = make_demo_data()
    data.to_excel("demo_wholesale_data.xlsx", index=False)
    print(f"Created demo_wholesale_data.xlsx with {len(data):,} rows.")
