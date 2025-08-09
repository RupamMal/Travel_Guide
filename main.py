import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import google.generativeai as genai


def load_environment_variables() -> None:
    """Load environment variables from a local .env file if present.

    Attempts to load from the directory containing this file so it works
    regardless of the current working directory.
    """
    dotenv_path = Path(__file__).resolve().parent / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path, override=False)
    else:
        # Fallback to default lookup (current working directory)
        load_dotenv(override=False)


def get_env_variable(name: str) -> Optional[str]:
    value = os.getenv(name)
    return value if value and value.strip() else None


def build_prompt(
    destination: str,
    days: int,
    month: Optional[str],
    currency: str,
    daily_budget: Optional[int],
) -> str:
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


def sanitize_filename(name: str) -> str:
    """Create a safe filename from a destination string for Windows/macOS/Linux."""
    safe = "".join(ch for ch in name if ch.isalnum() or ch in (" ", "-", "_"))
    safe = "_".join(safe.strip().split())
    return safe[:100] if safe else "travel_guide"


def save_output_markdown(destination: str, content: str) -> Path:
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    filename = sanitize_filename(destination) + ".md"
    out_path = reports_dir / filename
    out_path.write_text(content, encoding="utf-8")
    return out_path


def generate_travel_guide(
    model: str,
    destination: str,
    days: int,
    month: Optional[str],
    currency: str,
    daily_budget: Optional[int],
) -> str:
    system_message = (
        "You are a seasoned travel planner who creates accurate, helpful, and organized travel guides."
    )
    user_message = build_prompt(
        destination=destination,
        days=days,
        month=month,
        currency=currency,
        daily_budget=daily_budget,
    )

    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    generation_config = {
        "temperature": 0.6,
        "top_p": 0.9,
        "max_output_tokens": 2000,
    }
    model_client = genai.GenerativeModel(model)
    result = model_client.generate_content(
        [f"System: {system_message}", f"User: {user_message}"],
        generation_config=generation_config,
    )
    content = (getattr(result, "text", None) or "").strip()
    return content


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rupam's Travel Guide - Generate an LLM-based itinerary and travel info for a destination."
    )
    parser.add_argument(
        "--destination",
        required=True,
        help="Destination city/region/country, e.g. 'Tokyo' or 'Bali'",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=4,
        help="Number of days for the itinerary (default: 4)",
    )
    parser.add_argument(
        "--month",
        default=None,
        help="Optional month of travel to emphasize in precautions, e.g. 'September'",
    )
    parser.add_argument(
        "--currency",
        default="INR",
        help="Currency code/symbol for cost estimates (default: INR)",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=None,
        help="Approximate daily budget to target in the chosen currency (optional)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the model to use (defaults to MODEL env or gemini-1.5-flash)",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    load_environment_variables()

    args = parse_args(argv)

    model = (
        args.model
        or get_env_variable("MODEL")
        or "gemini-1.5-flash"
    )

    google_key = get_env_variable("GOOGLE_API_KEY")
    if not google_key:
        print(
            "ERROR: GOOGLE_API_KEY not set. Add it to .env or environment.",
            file=sys.stderr,
        )
        return 2

    try:
        content = generate_travel_guide(
            model=model,
            destination=args.destination,
            days=max(1, args.days),
            month=args.month,
            currency=args.currency,
            daily_budget=args.budget,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Failed to generate guide: {exc}", file=sys.stderr)
        return 1

    print(content)
    out_path = save_output_markdown(args.destination, content)
    print(f"\nSaved to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


