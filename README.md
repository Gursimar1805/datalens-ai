# 📊 DataLens AI

> Turn raw spreadsheets into clear, AI-generated insights — no formulas, no dashboards, no waiting.

**DataLens AI** is a web application that lets you upload your data (CSV/Excel) and get instant, AI-powered analysis streamed back to you in real time. Built for anyone who wants to *understand* their data without wrestling with pivot tables or writing a single line of pandas.

🔗 **Live App:** [datalens-ai-y8zs.onrender.com](https://datalens-ai-y8zs.onrender.com)
📦 **Repo:** [github.com/Gursimar1805/datalens-ai](https://github.com/Gursimar1805/datalens-ai)

---

## ✨ What It Does

1. **Upload** a CSV or Excel file straight from your browser.
2. **Ask/Analyze** — the app sends your data to an LLM which generates insights, summaries, and patterns.
3. **Watch it think** — responses are streamed token-by-token via Server-Sent Events (SSE), so you see the analysis unfold live instead of staring at a loading spinner.

No account setup. No manual charting. Just data in, insight out.

---

## 🧠 Why It's Different

Most "AI + data" tools either lock you into a heavyweight BI platform or require you to already know what question to ask. DataLens AI is intentionally minimal:

- **Zero-friction input** — drag in a spreadsheet, that's it.
- **Real-time feedback loop** — SSE streaming means you're reading insights as they're generated, not waiting on a single blocking API call.
- **Free-tier friendly AI** — runs on OpenRouter's `inclusionai/ling-3.0-flash:free` model, proving useful data analysis doesn't require an expensive API bill.
- **Containerized & reproducible** — the entire app ships as a Docker image, so "works on my machine" isn't a concern.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | **FastAPI** (Python) |
| Streaming | **Server-Sent Events (SSE)** |
| AI / LLM | **OpenRouter** → `inclusionai/ling-3.0-flash:free` |
| Data Handling | CSV / Excel parsing |
| Containerization | **Docker** |
| Deployment | **Render** |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Docker (optional, for containerized runs)
- An [OpenRouter](https://openrouter.ai/) API key

### Local Setup

\`\`\`bash
# Clone the repo
git clone https://github.com/Gursimar1805/datalens-ai.git
cd datalens-ai

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENROUTER_API_KEY=your_key_here

# Run the app
uvicorn main:app --reload
\`\`\`

Visit `http://localhost:8000` to start uploading files.

### Run with Docker

\`\`\`bash
docker build -t datalens-ai .
docker run -p 8000:8000 -e OPENROUTER_API_KEY=your_key_here datalens-ai
\`\`\`

---

## 📁 Project Structure

\`\`\`
datalens-ai/
├── main.py              # FastAPI app & SSE streaming logic
├── requirements.txt      # Python dependencies
├── Dockerfile             # Container definition
└── ...
\`\`\`

*(Adjust the tree above to match your actual repo layout.)*

---

## 🗺️ Roadmap

- [ ] Support for JSON and Google Sheets as input sources
- [ ] Downloadable insight reports (PDF/Markdown)
- [ ] Chart/visualization generation alongside text insights
- [ ] Multi-file / multi-sheet comparison analysis
- [ ] User accounts for saved analysis history

---

## 🙋 About

Built by **Gursimar Singh Kohli** — B.Tech CS (AI & ML) student, GenAI & Cloud Intern at BharatCares (AICTE–IBM SkillsBuild). DataLens AI was featured as the central project in the BharatCares GenAI & Cloud Computing Summer Training Report.

- GitHub: [@Gursimar1805](https://github.com/Gursimar1805)
- LinkedIn: [Gursimar Singh Kohli](https://linkedin.com/in/gursimar-singh-kohli-9b60a0255/)

---

## 📄 License

This project is open for learning and demonstration purposes. Add a formal license (MIT, Apache 2.0, etc.) if you plan to open it up for external contributions.
