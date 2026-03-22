
import os
import re
import json
import argparse
from typing import Optional
from dotenv import load_dotenv
import google.genai as genai
from PIL import Image


# ================= CONFIG =================
GEMINI_MODEL = "gemini-2.5-flash"
CHUNK_SIZE_CHARS    = 3000
OVERLAP_RATIO       = 0.0
MAX_CHUNKS          = 2
MAX_RETRIES         = 1


# ================= INIT =================
def load_api_key() -> str:
    load_dotenv()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise EnvironmentError("Missing GEMINI_API_KEY in .env")
    return key


def init_client(api_key: str):
    return genai.Client(api_key=api_key)


# ================= CHUNKING =================
def split_into_chunks(text: str, chunk_size: int) -> list[str]:
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i+chunk_size])
    return chunks


# ================= PROMPT =================
def build_prompt(text: str) -> str:
    return f"""
You are an expert privacy policy and legal contract analyzer, highly trained in the philosophy of 'ToS;DR' (Terms of Service; Didn't Read). 

First, carefully read the TEXT below. Then, rigorously analyze it for user rights violations and return a strict JSON array.

TEXT:
{text}

Format:
[
  {{
    "risk_level": "Red|Yellow|Green",
    "issue": "short description of the legal risk",
    "evidence": "exact quote from the text",
    "fix": "Specific legal recommendation to fix or mitigate"
  }}
]

Rules:
1. Identify dark patterns, hidden arbitration clauses, excessive data collection, and broad amendment rights according to ToS;DR standards.
2. Red = Critical risk (e.g., selling data, forced arbitration without opt-out).
3. Yellow = Warning (e.g., vague retention periods, broad marketing consent).
4. Green = Good practice (e.g., clear opt-outs, strict data minimization).
5. ANTI-HALLUCINATION TRIPLE CHECK: You MUST strictly ensure every single finding actually exists in the provided TEXT. The 'evidence' field must be an EXACT, word-for-word substring from the TEXT. Do NOT infer, hallucinate, or assume clauses that are not specifically written.
6. Max 5 most important findings.
7. Strict JSON only. No text or explanation outside the JSON brackets.
"""


# ================= JSON PARSE =================
def parse_json(raw: Optional[str]):
    if not raw:
        return []

    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if match:
        cleaned = match.group(1).strip()
    else:
        cleaned = raw.strip().strip("`").strip()

    try:
        return json.loads(cleaned)
    except:
        print("[WARN] Failed to parse JSON")
        return []


# ================= REPORT =================
def build_report(findings: list, filename: str):
    red = sum(1 for f in findings if f["risk_level"] == "Red")
    yellow = sum(1 for f in findings if f["risk_level"] == "Yellow")
    green = sum(1 for f in findings if f["risk_level"] == "Green")

    overall = "Green"
    if red > 0:
        overall = "Red"
    elif yellow > 0:
        overall = "Yellow"

    return {
        "document": filename,
        "overall_risk": overall,
        "summary": {
            "total": len(findings),
            "red": red,
            "yellow": yellow,
            "green": green
        },
        "findings": findings
    }


# ================= CORE LOGIC =================
def process_file(filepath: str) -> dict:
    api_key = load_api_key()
    client = init_client(api_key)

    is_image = False
    text = ""
    image_obj = None

    filename = os.path.basename(filepath)
    ext = filename.lower().split('.')[-1]
    
    if ext in ['png', 'jpg', 'jpeg', 'webp']:
        is_image = True
        try:
            image_obj = Image.open(filepath)
        except Exception as e:
            return {"error": f"Failed to read image: {e}"}
            
    elif ext == "pdf":
        try:
            import fitz
            doc = fitz.open(filepath)
            for page in doc:
                text += page.get_text()
        except ImportError:
            return {"error": "PyMuPDF (fitz) is not installed."}
        except Exception as e:
            return {"error": f"Failed to read PDF: {e}"}
            
    else:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            return {"error": f"Failed to read text file: {e}"}

    all_findings = []

    if is_image:
        print("[INFO] Processing Image Document...")
        prompt_text = "Please analyze the provided image containing an agreement/terms."
        prompt = build_prompt(prompt_text)
        
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[image_obj, prompt]
            )
            raw = response.text if hasattr(response, "text") else None
            parsed = parse_json(raw)
            if isinstance(parsed, list):
                all_findings.extend(parsed)
        except Exception as e:
            print(f"[ERROR] Gemini Image call failed: {e}")
            
    else:
        if len(text) > 8000:
            print("[INFO] Truncating large text document for demo...")
            text = text[:8000]

        chunks = split_into_chunks(text, CHUNK_SIZE_CHARS)
        chunks = chunks[:MAX_CHUNKS]

        for i, chunk in enumerate(chunks):
            print(f"[Processing chunk {i+1}]")
            prompt = build_prompt(chunk)
            
            try:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt
                )
                raw = response.text if hasattr(response, "text") else None
            except Exception as e:
                print(f"[ERROR] Gemini text call failed: {e}")
                raw = None
                
            parsed = parse_json(raw)
            if isinstance(parsed, list):
                all_findings.extend(parsed)

    return build_report(all_findings, filename)

# ================= CLI MAIN =================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--output", default="report.json")
    args = parser.parse_args()

    print("== LegaLens Minimal Version ==")
    
    report = process_file(args.file)
    
    if "error" in report:
        print(f"[FATAL ERROR] {report['error']}")
        return

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nAnalysis complete! Found {report.get('summary', {}).get('red', 0)} Critical, {report.get('summary', {}).get('yellow', 0)} Warning, and {report.get('summary', {}).get('green', 0)} Safe risks.")
    print(f"Detailed output has been saved to '{args.output}'.")
    print("Open 'index.html' in your browser to view the interactive dashboard!")

if __name__ == "__main__":
    main()