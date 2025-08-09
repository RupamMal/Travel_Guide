## Rupam's Travel Guide

Generate a complete, LLM-powered travel guide and itinerary for any destination.

### What it provides
- **Best time to visit**
- **Best hotels in the area** (with rough price ranges and links when possible)
- **Best local foods**
- **Month‑wise precautions**
- **Approximate costs** (daily budget and sample breakdown)
- **Foreigner visit rate** (qualitative + rough figures when known)
- **Day-by-day itinerary** with morning/afternoon/evening plans and tips

### Prerequisites
- Python 3.9+
- A Google Gemini API key (`GOOGLE_API_KEY`) in a `.env` file

### Setup (Windows PowerShell)
```powershell
cd E:\project
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Create a .env file with your Gemini key
@"
GOOGLE_API_KEY=
MODEL=gemini-1.5-flash
"@ | Out-File -Encoding utf8 .env
```

### Usage
Basic:
```powershell
python main.py --destination "Tokyo"
```

With options:
```powershell
python main.py \
  --destination "Bali" \
  --days 5 \
  --month "September" \
  --currency "INR" \
  --budget 150 \
  --model "gemini-1.5-pro"
```

Output is printed to the console and saved to `reports/<destination>.md`.

### Notes
- This tool uses a large language model. Some details (prices, links, opening hours) can change frequently. **Verify critical info before booking.**
- You can change the model with `--model`. Defaults to `gemini-1.5-flash` if not specified.
- If you need a strictly offline plan, the tool won’t be able to fetch live data. Consider enabling browsing in your own environment if you extend it.

### Gemini Models

Set `GOOGLE_API_KEY` and choose from available Gemini models:
- `gemini-1.5-flash` (default, faster)
- `gemini-1.5-pro` (more capable)

CLI examples:
- `python main.py --destination "Tokyo"` (uses default gemini-1.5-flash)
- `python main.py --destination "Tokyo" --model "gemini-1.5-pro"`

## Web app

### Run locally (Simple HTTP server)
```powershell
cd E:\project
.\.venv\Scripts\Activate.ps1
python server.py
```

Open `http://127.0.0.1:8000` in your browser. Enter destination and options, then generate the guide. The Markdown is also saved under `reports/` and rendered nicely in the browser.

### Deploy to Vercel (free hosting)
1. Push to GitHub (already done)
2. Go to https://vercel.com and import your repo
3. Set environment variables:
   - `GOOGLE_API_KEY` = your Gemini API key
   - `MODEL` = `gemini-1.5-flash`
4. Deploy

Your site will be live at a free Vercel URL!




