from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import re
from datetime import datetime

app = FastAPI()

class ExtractRequest(BaseModel):
    text: str

class InvoiceResponse(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str

@app.post("/extract", response_model=InvoiceResponse)
def extract_invoice(req: ExtractRequest):
    try:
        text = req.text
        if not text or not isinstance(text, str):
            raise ValueError("Empty or invalid input")

        # Fallback / extraction logic for structured fields
        # 1. Currency (3 uppercase letters like USD, EUR, GBP)
        currency_match = re.search(r'\b(USD|EUR|GBP|INR|CAD|AUD)\b', text, re.IGNORECASE)
        currency = currency_match.group(1).upper() if currency_match else "USD"

        # 2. Amount (floating point numbers near currency or total keywords)
        amount = 0.0
        amount_match = re.search(r'(?:total|due|amount|sum|balance)?[:\s]*[\$€£]?\s*(\d{1,5}(?:,\d{3})*(?:\.\d{2})?)', text, re.IGNORECASE)
        if amount_match:
            amt_str = amount_match.group(1).replace(",", "")
            amount = float(amt_str)

        # 3. Date (YYYY-MM-DD format)
        date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
        date_str = date_match.group(1) if date_match else datetime.today().strftime('%Y-%m-%d')

        # 4. Vendor (extract company/industries name or words before invoice)
        vendor = "Unknown Vendor"
        vendor_match = re.search(r'([A-Za-z0-9\-]+ (?:Industries|Corp|Inc|LLC|Ltd|Co)\b)', text, re.IGNORECASE)
        if vendor_match:
            vendor = vendor_match.group(1)
        else:
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            if lines:
                vendor = lines[0][:50]

        return {
            "vendor": vendor,
            "amount": amount,
            "currency": currency,
            "date": date_str
        }
    except Exception:
        # Prevent 500 error on garbage input; return safe fallback or 422
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "Malformed or unprocessable input"}
        )