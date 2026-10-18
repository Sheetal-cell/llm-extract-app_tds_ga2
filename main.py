from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
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

        # 1. CURRENCY
        currency_match = re.search(r'\b(USD|EUR|GBP|INR|CAD|AUD|CHF|JPY|NZD)\b', text, re.IGNORECASE)
        currency = currency_match.group(1).upper() if currency_match else "USD"

        # 2. DATE (YYYY-MM-DD)
        date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
        date_str = date_match.group(1) if date_match else datetime.today().strftime('%Y-%m-%d')

        # 3. AMOUNT EXTRACTION
        # First priority: Look for explicit total/amount due patterns
        total_patterns = [
            r'(?:total\s*due|amount\s*due|grand\s*total|total\s*amount|total)[:\s]*[\$€£]?\s*([0-9,]+\.\d{2})',
            r'(?:total\s*due|amount\s*due|grand\s*total|total\s*amount|total)[:\s]*[\$€£]?\s*([0-9,]+)',
            r'[\$€£]\s*([0-9,]+\.\d{2})'
        ]
        
        amount = None
        for pattern in total_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Pick the last match for explicit total keywords, or format floats properly
                val_str = matches[-1].replace(',', '')
                try:
                    amount = float(val_str)
                    break
                except ValueError:
                    continue

        # Fallback for amount: Find all numbers with decimals and take the maximum
        if amount is None:
            all_floats = re.findall(r'\b\d{1,6}\.\d{2}\b', text)
            if all_floats:
                # Exclude strings that match the date components (e.g. month or day)
                valid_nums = []
                for num_str in all_floats:
                    if num_str not in date_str:
                        valid_nums.append(float(num_str))
                if valid_nums:
                    amount = max(valid_nums)

        if amount is None:
            amount = 0.0

        # 4. VENDOR EXTRACTION
        vendor = "Unknown Vendor"
        
        # Check for explicit "Vendor:", "From:", "Billed By:" labels
        vendor_label_match = re.search(r'(?:vendor|from|billed\s*by|company|seller)[:\s]+([^\n\r]+)', text, re.IGNORECASE)
        if vendor_label_match:
            vendor = vendor_label_match.group(1).strip()
        else:
            # Check for standard company suffix patterns
            corp_match = re.search(r'([A-Za-z0-9\-\.\s]+(?:Industries|Corp|Corporation|Inc|LLC|Ltd|Limited|Co|Company)\b)', text, re.IGNORECASE)
            if corp_match:
                vendor = corp_match.group(1).strip()
            else:
                # Fallback to the first non-empty line
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                if lines:
                    vendor = lines[0][:60]

        return {
            "vendor": vendor,
            "amount": amount,
            "currency": currency,
            "date": date_str
        }

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "Malformed or unprocessable input"}
        )