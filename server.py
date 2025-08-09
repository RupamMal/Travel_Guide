import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from dotenv import load_dotenv
import google.generativeai as genai


PROJECT_DIR = Path(__file__).resolve().parent
WEB_DIR = PROJECT_DIR / "web"
REPORTS_DIR = PROJECT_DIR / "reports"


def load_env() -> None:
    dotenv_path = PROJECT_DIR / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path, override=False)
    else:
        load_dotenv(override=False)


def sanitize_filename(name: str) -> str:
    safe = "".join(ch for ch in name if ch.isalnum() or ch in (" ", "-", "_"))
    safe = "_".join(safe.strip().split())
    return safe[:100] if safe else "travel_guide"


def build_prompt(destination: str, days: int, month, currency: str, daily_budget):
    specific_month_line = (
        f"If the user-specified month is provided, highlight guidance for {month} explicitly."
        if month
        else ""
    )
    budget_line = (
        f"Assume a daily budget of around {daily_budget} {currency} and adjust recommendations accordingly."
        if daily_budget is not None
        else ""
    )
    return f"""
You are an expert travel planner. Generate a complete, accurate, and helpful travel guide in clear Markdown for the destination: {destination}.

Output structure (use Markdown headings and bullet lists; keep it concise but complete):

1. Title: "Rupam's Travel Guide: {destination}"
2. One-paragraph overview
3. Best time to visit: months, weather patterns, crowd levels
4. Foreigner visit rate: qualitative plus rough figures or indexes when commonly known; else a careful qualitative estimate
5. Approximate costs in {currency}:
   - Daily budget ranges (shoestring / mid-range / comfortable)
   - Typical costs: accommodation per night, meals, local transport, attractions
   - Example total for {days} days
6. Best hotels in the area: 3-6 options across budget/mid-range/luxury with rough price range in {currency}; include neighborhood context; if widely-known, add an official site or aggregator keyword (no live browsing)
7. Best local foods: 6-10 iconic dishes/snacks/drinks with one-line descriptions
8. Month-wise precautions: cover all 12 months with concise bullets (weather, closures, festivals, health, clothing). {specific_month_line}
9. Itinerary for {days} days: for each day, outline morning/afternoon/evening with 2-3 attraction ideas, approximate visit durations, transit suggestions, timing tips, and alternatives for rain/peak heat
10. Practical tips: safety, payments, SIM/internet, etiquette, local transport passes, tipping norms, scams to avoid

General guidance:
- If specific facts are uncertain, label them as estimates and provide typical ranges. Do not fabricate precise numbers.
- Keep suggestions family-friendly and culturally sensitive.
- Avoid promises; use cautious language when needed.
- Use readable Markdown with headings, bullet points, and short paragraphs.
- Do not include any system or meta-instructions in the final answer.
{budget_line}
"""


class GuideHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def _send_json(self, status: int, data: dict) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):  # noqa: N802 (stdlib name)
        if self.path != "/api/generate":
            return super().do_POST()

        length = int(self.headers.get("Content-Length", "0"))
        try:
            body_bytes = self.rfile.read(length)
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception as exc:  # noqa: BLE001
            return self._send_json(400, {"ok": False, "error": f"Invalid JSON: {exc}"})

        destination = (data.get("destination") or "").strip()
        if not destination:
            return self._send_json(400, {"ok": False, "error": "'destination' is required"})

        days = data.get("days") or 4
        try:
            days = max(1, int(days))
        except Exception:
            days = 4

        month = (data.get("month") or "").strip() or None
        currency = (data.get("currency") or "INR").strip() or "INR"

        daily_budget = data.get("budget")
        try:
            daily_budget = int(daily_budget) if daily_budget is not None else None
        except Exception:
            daily_budget = None

        model = (data.get("model") or os.getenv("MODEL") or "gemini-1.5-flash").strip()

        google_key = os.getenv("GOOGLE_API_KEY")
        if not google_key:
            return self._send_json(500, {"ok": False, "error": "GOOGLE_API_KEY not set"})
        genai.configure(api_key=google_key)

        system_message = (
            "You are a seasoned travel planner who creates accurate, helpful, and organized travel guides."
        )

        prompt = build_prompt(
            destination=destination, days=days, month=month, currency=currency, daily_budget=daily_budget
        )

        try:
            generation_config = {
                "temperature": 0.6,
                "top_p": 0.9,
                "max_output_tokens": 2000,
            }
            model_client = genai.GenerativeModel(model)
            result = model_client.generate_content(
                [f"System: {system_message}", f"User: {prompt}"],
                generation_config=generation_config,
            )
            content = (getattr(result, "text", None) or "").strip()
        except Exception as exc:  # noqa: BLE001
            return self._send_json(500, {"ok": False, "error": f"Failed to generate: {exc}"})

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        file_path = REPORTS_DIR / f"{sanitize_filename(destination)}.md"
        file_path.write_text(content, encoding="utf-8")

        return self._send_json(200, {"ok": True, "markdown": content, "saved": str(file_path)})


def main() -> None:
    load_env()
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    server = HTTPServer((host, port), GuideHandler)
    print(f"Serving simple site on http://{host}:{server.server_port}")
    print("Open your browser to the URL above.")
    server.serve_forever()


if __name__ == "__main__":
    main()


