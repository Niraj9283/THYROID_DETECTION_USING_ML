"""
ThyroScan — Lab Report Parser & OCR Extraction Service
Extracts clinical thyroid biomarker values (TSH, T3, TT4, T4U, FTI)
from uploaded diagnostic lab reports (PDF, images, text) with user verification.
"""

import re
import io
from pypdf import PdfReader


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extracts text content from uploaded PDF bytes."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""


def parse_lab_parameters_from_text(raw_text: str) -> dict:
    """
    Parses key clinical thyroid parameters from unstructured diagnostic report text
    using robust medical entity regex patterns.
    """
    extracted = {
        'TSH': None,
        'T3': None,
        'TT4': None,
        'T4U': None,
        'FTI': None,
        'age': None,
        'sex': None
    }
    confidence = {}
    snippets = {}

    lines = raw_text.splitlines()

    # Regex patterns for biomarkers
    patterns = {
        'TSH': [
            r'(?:TSH|Thyroid\s+Stimulating\s+Hormone|Thyrotropin)[^\d\n]*[:=\-]?\s*([0-9]+\.?[0-9]*)',
            r'\bTSH\b[^\n\d]*([0-9]+\.[0-9]+)',
            r'Ultrasensitive\s+TSH[^\d\n]*([0-9]+\.?[0-9]*)'
        ],
        'T3': [
            r'(?:Total\s+T3|Triiodothyronine\s+Total|T3\s+Total|T3)[^\d\n]*[:=\-]?\s*([0-9]+\.?[0-9]*)',
            r'\bTotal\s+T3\b[^\n\d]*([0-9]+\.[0-9]+)',
            r'\bT3\b[^\n\d]*[:=\-]?\s*([0-9]+\.?[0-9]*)'
        ],
        'TT4': [
            r'(?:Total\s+T4|Thyroxine\s+Total|TT4|T4\s+Total|Total\s+Thyroxine)[^\d\n]*[:=\-]?\s*([0-9]+\.?[0-9]*)',
            r'\bTT4\b[^\n\d]*([0-9]+\.[0-9]+)',
            r'\bTotal\s+T4\b[^\n\d]*([0-9]+\.?[0-9]*)'
        ],
        'T4U': [
            r'(?:T4\s+Uptake|T4U|Thyroid\s+Uptake)[^\d\n]*[:=\-]?\s*([0-9]+\.?[0-9]*)',
            r'\bT4U\b[^\n\d]*([0-9]+\.[0-9]+)'
        ],
        'FTI': [
            r'(?:Free\s+Thyroxine\s+Index|FTI|Free\s+T4\s+Index)[^\d\n]*[:=\-]?\s*([0-9]+\.?[0-9]*)',
            r'\bFTI\b[^\n\d]*([0-9]+\.[0-9]+)'
        ],
        'age': [
            r'(?:Age|Age/Gender|Age/Sex)[^\d\n]*[:=\-]?\s*([0-9]{1,3})',
            r'([0-9]{1,3})\s*(?:Yrs|Years|Y/O|Year\s+Old)'
        ],
        'sex': [
            r'(?:Sex|Gender)[^\w\n]*[:=\-]?\s*(Male|Female|M|F)\b',
            r'\b(Male|Female)\b'
        ]
    }

    # Iterate over text and match patterns
    for param, reg_list in patterns.items():
        for reg in reg_list:
            match = re.search(reg, raw_text, re.IGNORECASE)
            if match:
                raw_val = match.group(1).strip()
                if param == 'sex':
                    val_lower = raw_val.lower()
                    extracted['sex'] = 1 if val_lower.startswith('m') else 0
                    confidence['sex'] = 90
                    snippets['sex'] = match.group(0)
                    break
                else:
                    try:
                        num_val = float(raw_val)
                        # Sanity checks for ranges
                        if param == 'age' and (0 < num_val <= 120):
                            extracted['age'] = int(num_val)
                            confidence['age'] = 88
                            snippets['age'] = match.group(0)
                            break
                        elif param == 'TSH' and (0 <= num_val <= 200):
                            extracted['TSH'] = num_val
                            confidence['TSH'] = 92
                            snippets['TSH'] = match.group(0)
                            break
                        elif param == 'T3' and (0 <= num_val <= 20):
                            extracted['T3'] = num_val
                            confidence['T3'] = 89
                            snippets['T3'] = match.group(0)
                            break
                        elif param == 'TT4' and (0 <= num_val <= 300):
                            extracted['TT4'] = num_val
                            confidence['TT4'] = 91
                            snippets['TT4'] = match.group(0)
                            break
                        elif param == 'T4U' and (0 <= num_val <= 5):
                            extracted['T4U'] = num_val
                            confidence['T4U'] = 85
                            snippets['T4U'] = match.group(0)
                            break
                        elif param == 'FTI' and (0 <= num_val <= 400):
                            extracted['FTI'] = num_val
                            confidence['FTI'] = 87
                            snippets['FTI'] = match.group(0)
                            break
                    except ValueError:
                        continue

    # Count how many parameters found
    found_count = sum(1 for v in extracted.values() if v is not None)

    return {
        'extracted': extracted,
        'confidence': confidence,
        'snippets': snippets,
        'found_count': found_count,
        'raw_text_snippet': raw_text[:600] if raw_text else "No extractable text found."
    }
