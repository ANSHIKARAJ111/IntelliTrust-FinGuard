import hashlib
from datetime import datetime
import pandas as pd

ALIASES = {
    "date": ["date", "transaction date", "txn_date", "transaction_date"],
    "description": ["description", "details", "narration", "merchant"],
    "amount": ["amount", "transaction amount", "debit", "withdrawal"],
    "type": ["type", "transaction type", "txn_type"],
}

def find_col(columns, names):
    lower = {c.lower().strip(): c for c in columns}
    for n in names:
        if n in lower: return lower[n]
    return None

def categorize(text: str) -> str:
    t = text.lower()
    rules = {
        "Food": ["swiggy","zomato","restaurant","cafe","starbucks"],
        "Shopping": ["amazon","flipkart","myntra","shopping"],
        "Travel": ["uber","ola","metro","flight","irctc"],
        "Bills": ["electricity","airtel","jio","recharge","bill"],
        "Income": ["salary","credit","stipend"],
    }
    for cat, words in rules.items():
        if any(w in t for w in words): return cat
    return "Other"

def parse_statement(file_obj):
    df = pd.read_csv(file_obj)
    date_col = find_col(df.columns, ALIASES["date"])
    desc_col = find_col(df.columns, ALIASES["description"])
    amount_col = find_col(df.columns, ALIASES["amount"])
    type_col = find_col(df.columns, ALIASES["type"])
    if not date_col or not desc_col or not amount_col:
        raise ValueError("CSV must contain date, description and amount columns")
    rows=[]
    for _, r in df.iterrows():
        desc=str(r[desc_col]).strip()
        amount=float(str(r[amount_col]).replace(",","").replace("₹","").strip())
        dt=pd.to_datetime(r[date_col]).to_pydatetime()
        txn_type=str(r[type_col]).lower().strip() if type_col else ("credit" if "salary" in desc.lower() else "debit")
        fp=hashlib.sha256(f"{dt.isoformat()}|{desc}|{amount}|{txn_type}".encode()).hexdigest()
        rows.append({"txn_date":dt,"description":desc,"merchant":desc[:120],"category":categorize(desc),"amount":abs(amount),"txn_type":txn_type,"fingerprint":fp})
    return rows
