# backend/job_inspection/job_inspect_llm.py

import os
import json
import textwrap
import requests
from bs4 import BeautifulSoup
from openai import OpenAI


# ------------ CONFIG ------------

def _get_openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set. "
            "Set it locally and via `flyctl secrets set OPENAI_API_KEY=...`."
        )
    return OpenAI(api_key=api_key)


# ------------ LLM CALL ------------

def call_llm_for_job_analysis(page_text: str, url: str) -> dict:
    client = _get_openai_client()

    system_prompt = """
You are a job posting analysis assistant.

Your task:
1. Decide if the given page text represents a realistic job posting.
2. If it does, extract key fields into a JSON object with a fixed schema.
3. If it does not, still fill the JSON, but set is_valid_job_posting = false and explain why.

Important rules:
- Always respond with VALID JSON ONLY.
- Do not include any explanations outside the JSON.
- If a field is missing or unknown, use null or "Unknown" as appropriate.
- When extracting dates for internships or co-ops, try to infer:
  * Start month (numeric, 1–12) and year (e.g. 2026)
  * End month (numeric, 1–12) and year (e.g. 2026)
  If no clear internship/term dates are specified, set those fields to null.
""".strip()

    user_prompt = f"""
Here is the job posting page text (may be noisy):

PAGE_URL: {url}

PAGE_TEXT:
\"\"\"{page_text}\"\"\"

Return a single JSON object with this exact schema:

{{
  "is_valid_job_posting": boolean,
  "validity_reason": string,

  "job_title": string or null,
  "company_name": string or null,
  "location": string or null,   // e.g. "Seattle, WA" when possible

  "work_model": string,         // e.g. "On-site", "Remote", "Hybrid", or "Unknown"
  "salary_currency": string or null,
  "salary_min": number or null,
  "salary_max": number or null,
  "salary_interval": string,    // e.g. "hourly", "yearly", "Unknown"
  "employment_type": string,    // e.g. "Full-time", "Internship", "Contract", or "Unknown",
  "application_deadline": string or null, // keep as free-text date or "Unknown"
  "job_url": string,

  // Internship / Co-op timing (approximate if needed)
  "job_start_month": number or null, // 1-12
  "job_start_year": number or null,  // e.g. 2026
  "job_end_month": number or null,   // 1-12
  "job_end_year": number or null,    // e.g. 2026

  "red_flags": [string, ...],
  "quick_summary": string,
  "raw_snippet": string
}}

Rules:
- "location" should be as close as possible to "City, ST" format if that information is available (e.g. "Seattle, WA").
- If you cannot confidently identify job start or end month/year, set the corresponding fields to null.
- Remember: respond with JSON only.
""".strip()

    # Using Chat Completions; model name can be gpt-4.1-mini or gpt-4o-mini depending on your account
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )

    content = response.choices[0].message.content

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON: {e}\nRaw content:\n{content}")

    return data


def analyze_job_url(url: str) -> dict:
    """
    High-level helper for backend usage.
    Given a job posting URL, fetch the page, run LLM, return structured dict.
    """
    page_text = fetch_page_text(url)
    result = call_llm_for_job_analysis(page_text, url)
    return result


# ------------ HTML FETCH / TEXT EXTRACTION ------------

def fetch_page_text(url: str, max_chars: int = 12000) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (WhatsTheMove Job Inspector)"
    }
    resp = requests.get(url, timeout=10, headers=headers)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Strip script/style/noscript
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    # Collapse whitespace
    text = "\n".join(
        line.strip()
        for line in text.splitlines()
        if line.strip()
    )

    return text[:max_chars]


# ------------ (Optional) CLI for local debugging ------------

def pretty_print_result(result: dict) -> None:
    print("\n================= JOB ANALYSIS RESULT =================\n")

    is_valid = result.get("is_valid_job_posting")
    print(f"Valid job posting?  {is_valid}")
    print(f"Reason:            {result.get('validity_reason')}\n")

    print("Basic Info")
    print("----------")
    print(f"Job Title:         {result.get('job_title')}")
    print(f"Company:           {result.get('company_name')}")
    print(f"Location:          {result.get('location')}")
    print(f"Work Model:        {result.get('work_model')}")
    print(f"Employment Type:   {result.get('employment_type')}")
    print(f"Application Deadline: {result.get('application_deadline')}")
    print(f"Job URL:           {result.get('job_url')}\n")

    print("Compensation")
    print("------------")
    print(f"Currency:          {result.get('salary_currency')}")
    print(f"Salary Interval:   {result.get('salary_interval')}")
    print(f"Salary Min:        {result.get('salary_min')}")
    print(f"Salary Max:        {result.get('salary_max')}\n")

    red_flags = result.get("red_flags") or []
    if red_flags:
        print("Red Flags")
        print("---------")
        for rf in red_flags:
            print(f"- {rf}")
        print()

    summary = result.get("quick_summary") or ""
    if summary:
        print("Summary")
        print("-------")
        print(textwrap.fill(summary, width=80))
        print()

    snippet = result.get("raw_snippet") or ""
    if snippet:
        print("Raw Snippet")
        print("-----------")
        print(textwrap.fill(snippet, width=80))
        print()

    print("Full JSON (for debugging / frontend wiring)")
    print("-------------------------------------------")
    print(json.dumps(result, indent=2))


def main():
    print("=== WhatsTheMove Job Posting Inspector (Terminal Version) ===")
    url = input("Paste a job posting URL and press Enter:\n> ").strip()

    if not url:
        print("No URL provided, exiting.")
        return

    if not (url.startswith("http://") or url.startswith("https://")):
        print("URL must start with http:// or https://")
        return

    print("\nFetching and analyzing page... this may take a few seconds...\n")

    try:
        page_text = fetch_page_text(url)
    except Exception as e:
        print(f"Error fetching page: {e}")
        return

    try:
        result = call_llm_for_job_analysis(page_text, url)
    except Exception as e:
        print(f"Error during LLM analysis: {e}")
        return

    pretty_print_result(result)


if __name__ == "__main__":
    main()
