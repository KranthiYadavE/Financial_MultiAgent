"""
Generate synthetic financial data + FAQ/policy documents.
Bronze (raw) → Silver (cleaned) → Gold (relational + docs).
100% local — no external APIs.
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

fake = Faker("en_IN")
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

CATEGORIES = ["groceries", "utilities", "salary", "transfer", "emi", "shopping", "fuel", "dining"]
TXN_TYPES = ["debit", "credit"]
MERCHANTS = {
    "groceries": ["BigBasket", "DMart", "Reliance Fresh"],
    "utilities": ["BESCOM", "Airtel", "Jio"],
    "salary": ["Employer Corp", "Payroll Services"],
    "transfer": ["NEFT Transfer", "UPI Transfer"],
    "emi": ["HDFC Loan", "SBI Home Loan"],
    "shopping": ["Amazon", "Flipkart", "Myntra"],
    "fuel": ["Indian Oil", "HP Petrol"],
    "dining": ["Swiggy", "Zomato", "Cafe Coffee Day"],
}


def _random_pan() -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return (
        "".join(random.choices(letters, k=5))
        + "".join(random.choices("0123456789", k=4))
        + random.choice(letters)
    )


def generate_customers(n: int = 50) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        rows.append(
            {
                "customer_id": i,
                "full_name": fake.name(),
                "email": fake.email(),
                "phone": fake.phone_number()[:15],
                "pan": _random_pan(),
                "account_number": f"{random.randint(10**15, 10**16 - 1)}",
                "kyc_status": random.choice(["verified", "pending", "verified"]),
                "created_at": fake.date_time_between(start_date="-2y", end_date="now").isoformat(),
            }
        )
    return pd.DataFrame(rows)


def generate_transactions(customers: pd.DataFrame, per_customer: int = 30) -> pd.DataFrame:
    rows = []
    txn_id = 1
    for _, cust in customers.iterrows():
        for _ in range(per_customer):
            cat = random.choice(CATEGORIES)
            txn_type = "credit" if cat == "salary" else random.choice(TXN_TYPES)
            amount = round(random.uniform(50, 50000), 2)
            if cat == "salary":
                amount = round(random.uniform(30000, 150000), 2)
            txn_date = fake.date_between(start_date="-180d", end_date="today")
            rows.append(
                {
                    "transaction_id": txn_id,
                    "customer_id": int(cust["customer_id"]),
                    "account_number": cust["account_number"],
                    "transaction_date": txn_date.isoformat(),
                    "transaction_type": txn_type,
                    "category": cat,
                    "merchant": random.choice(MERCHANTS[cat]),
                    "amount": amount,
                    "currency": "INR",
                    "status": random.choice(["completed", "completed", "completed", "pending"]),
                    "description": f"{txn_type.title()} at {cat}",
                    "created_at": date.today().isoformat(),
                }
            )
            txn_id += 1
    return pd.DataFrame(rows)


def generate_policy_docs() -> list[dict]:
    """FAQ and policy documents for RAG ingestion."""
    docs = [
        {
            "id": "faq-001",
            "title": "Account Opening Requirements",
            "category": "faq",
            "content": (
                "To open a savings account, you need valid government ID (Aadhaar, PAN), "
                "proof of address, and a minimum deposit of INR 1,000. KYC verification "
                "is mandatory within 30 days. Minor accounts require a guardian's documents."
            ),
        },
        {
            "id": "faq-002",
            "title": "NEFT and RTGS Transfer Limits",
            "category": "faq",
            "content": (
                "NEFT transfers have no minimum amount and process in hourly batches. "
                "RTGS requires a minimum of INR 2 lakhs and settles in real time during "
                "banking hours (9 AM - 4:30 PM IST). Daily transfer limits depend on your "
                "KYC tier: Tier 1 allows INR 1 lakh/day, Tier 2 allows INR 5 lakhs/day."
            ),
        },
        {
            "id": "faq-003",
            "title": "Transaction Dispute Process",
            "category": "faq",
            "content": (
                "Report unauthorized transactions within 3 working days via the mobile app "
                "or branch. We will provisionally credit your account within 10 days while "
                "investigating. Provide transaction ID, date, and merchant name. "
                "Chargeback for card transactions may take 45-90 days."
            ),
        },
        {
            "id": "policy-001",
            "title": "Data Privacy Policy",
            "category": "policy",
            "content": (
                "We collect personal data only for KYC, transaction processing, and regulatory "
                "compliance. PAN, account numbers, and contact details are encrypted at rest. "
                "We never share data with third parties without consent except as required by RBI. "
                "Customers may request data export or deletion subject to legal retention periods."
            ),
        },
        {
            "id": "policy-002",
            "title": "Anti-Money Laundering (AML) Policy",
            "category": "policy",
            "content": (
                "Transactions above INR 10 lakhs are flagged for enhanced due diligence. "
                "Structuring (splitting large amounts) is prohibited. Suspicious activity "
                "must be reported to FIU-IND within 7 days. Cash deposits above INR 50,000 "
                "require PAN verification. Cross-border transfers require purpose code declaration."
            ),
        },
        {
            "id": "policy-003",
            "title": "Interest Rate and Fee Schedule",
            "category": "policy",
            "content": (
                "Savings account interest: 3.5% per annum, calculated daily and credited quarterly. "
                "ATM withdrawals: first 5 free per month, INR 20 per additional withdrawal. "
                "NEFT: INR 5 per transaction. RTGS: INR 25 per transaction. "
                "Account maintenance: waived if average monthly balance exceeds INR 10,000."
            ),
        },
        {
            "id": "faq-004",
            "title": "How to View Transaction History",
            "category": "faq",
            "content": (
                "You can view transactions in the mobile app under Accounts > Transaction History. "
                "Filter by date range, category, or amount. Export up to 12 months as PDF or CSV. "
                "For statements older than 12 months, visit a branch or use internet banking."
            ),
        },
        {
            "id": "faq-005",
            "title": "EMI and Loan Repayment",
            "category": "faq",
            "content": (
                "EMI auto-debit occurs on the 5th of each month. Ensure sufficient balance "
                "by the 4th to avoid bounce charges of INR 500. Prepayment is allowed with "
                "no penalty after 12 EMIs. Partial prepayment reduces principal and recalculates EMI."
            ),
        },
    ]
    return docs


def run_pipeline(customer_count: int = 50, txns_per_customer: int = 30) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "bronze").mkdir(exist_ok=True)
    (DATA / "silver").mkdir(exist_ok=True)
    (DATA / "gold").mkdir(exist_ok=True)
    (DATA / "docs").mkdir(exist_ok=True)

    # Bronze: raw-ish exports (simulating upstream feeds)
    customers = generate_customers(customer_count)
    transactions = generate_transactions(customers, txns_per_customer)

    customers.to_parquet(DATA / "bronze" / "customers_raw.parquet", index=False)
    transactions.to_parquet(DATA / "bronze" / "transactions_raw.parquet", index=False)

    # Silver: cleaned + normalized
    customers_silver = customers.copy()
    customers_silver["email"] = customers_silver["email"].str.lower().str.strip()
    customers_silver["phone"] = customers_silver["phone"].str.replace(r"\D", "", regex=True)
    customers_silver["kyc_status"] = customers_silver["kyc_status"].str.lower()

    transactions_silver = transactions.copy()
    transactions_silver["transaction_date"] = pd.to_datetime(transactions_silver["transaction_date"])
    transactions_silver["amount"] = transactions_silver["amount"].astype(float)
    transactions_silver = transactions_silver[transactions_silver["status"] == "completed"]

    customers_silver.to_parquet(DATA / "silver" / "customers_clean.parquet", index=False)
    transactions_silver.to_parquet(DATA / "silver" / "transactions_clean.parquet", index=False)

    # Gold: analytics-ready parquet + docs
    customers_silver.to_parquet(DATA / "gold" / "customers.parquet", index=False)
    transactions_silver.to_parquet(DATA / "gold" / "transactions.parquet", index=False)

    docs = generate_policy_docs()
    with open(DATA / "docs" / "faq_policies.json", "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2)

    for doc in docs:
        path = DATA / "docs" / f"{doc['id']}.txt"
        path.write_text(f"# {doc['title']}\n\n{doc['content']}", encoding="utf-8")

    print(f"Generated {len(customers)} customers, {len(transactions_silver)} transactions")
    print(f"Generated {len(docs)} FAQ/policy documents")
    print(f"Data written to {DATA}")


if __name__ == "__main__":
    run_pipeline()
