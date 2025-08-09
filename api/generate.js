export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ ok: false, error: 'Method Not Allowed' });
  }

  try {
    const {
      destination = '',
      days = 4,
      month = '',
      currency = 'INR',
      budget = undefined,
      model: rawModel = process.env.MODEL || 'gemini-1.5-flash',
    } = req.body || {};

    const model = String(rawModel || '').trim();

    if (!destination.trim()) {
      return res.status(400).json({ ok: false, error: "'destination' is required" });
    }

    const daysInt = Math.max(1, parseInt(days, 10) || 4);
    const dailyBudget = budget != null && String(budget).trim() !== '' ? parseInt(budget, 10) : undefined;

    const prompt = buildPrompt({ destination, days: daysInt, month: month || undefined, currency, dailyBudget });
    const systemMessage = 'You are a seasoned travel planner who creates accurate, helpful, and organized travel guides.';

    const apiKey = process.env.GOOGLE_API_KEY;
    if (!apiKey) {
      return res.status(500).json({ ok: false, error: 'GOOGLE_API_KEY not set' });
    }

    const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${apiKey}`;
    const body = {
      contents: [
        { role: 'user', parts: [{ text: `System: ${systemMessage}` }] },
        { role: 'user', parts: [{ text: `User: ${prompt}` }] },
      ],
      generationConfig: { temperature: 0.6, topP: 0.9, maxOutputTokens: 2000 },
    };
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      const errText = await r.text();
      return res.status(500).json({ ok: false, error: `Gemini error: ${r.status} ${errText}` });
    }
    const data = await r.json();
    const parts = data?.candidates?.[0]?.content?.parts;
    const markdown = (parts && parts.map(p => p.text).join('\n')) || '';

    return res.status(200).json({ ok: true, markdown });
  } catch (err) {
    return res.status(500).json({ ok: false, error: String(err?.message || err) });
  }
}

function buildPrompt({ destination, days, month, currency, dailyBudget }) {
  const monthLine = month ? `If the user-specified month is provided, highlight guidance for ${month} explicitly.` : '';
  const budgetLine = Number.isFinite(dailyBudget) ? `Assume a daily budget of around ${dailyBudget} ${currency} and adjust recommendations accordingly.` : '';
  return `You are an expert travel planner. Generate a complete, accurate, and helpful travel guide in clear Markdown for the destination: ${destination}.

Output structure (use Markdown headings and bullet lists; keep it concise but complete):

1. Title: "Rupam's Travel Guide: ${destination}"
2. One-paragraph overview
3. Best time to visit: months, weather patterns, crowd levels
4. Foreigner visit rate: qualitative plus rough figures or indexes when commonly known; else a careful qualitative estimate
5. Approximate costs in ${currency}:
   - Daily budget ranges (shoestring / mid-range / comfortable)
   - Typical costs: accommodation per night, meals, local transport, attractions
   - Example total for ${days} days
6. Best hotels in the area: 3-6 options across budget/mid-range/luxury with rough price range in ${currency}; include neighborhood context; if widely-known, add an official site or aggregator keyword (no live browsing)
7. Best local foods: 6-10 iconic dishes/snacks/drinks with one-line descriptions
8. Month-wise precautions: cover all 12 months with concise bullets (weather, closures, festivals, health, clothing). ${monthLine}
9. Itinerary for ${days} days: for each day, outline morning/afternoon/evening with 2-3 attraction ideas, approximate visit durations, transit suggestions, timing tips, and alternatives for rain/peak heat
10. Practical tips: safety, payments, SIM/internet, etiquette, local transport passes, tipping norms, scams to avoid

General guidance:
- If specific facts are uncertain, label them as estimates and provide typical ranges. Do not fabricate precise numbers.
- Keep suggestions family-friendly and culturally sensitive.
- Avoid promises; use cautious language when needed.
- Use readable Markdown with headings, bullet points, and short paragraphs.
- Do not include any system or meta-instructions in the final answer.
${budgetLine}`;
}


