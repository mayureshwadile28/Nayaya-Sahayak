# ⚖️ Nyaya Sahayak (न्याय सहायक)
### *Democratizing Legal Literacy & Empowering Citizens Through GenAI*

[![Vercel Deployment](https://img.shields.io/badge/Deployed%20on-Vercel-black?style=for-the-badge&logo=vercel)](https://nayaya-sahayak.vercel.app)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Google Gemini](https://img.shields.io/badge/Google%20GenAI-Gemini%20Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

---

## 📌 Executive Summary

Over **40 million cases** are currently pending across Indian courts. Millions more never reach an advocate or tribunal because ordinary citizens are intimidated by dense legal legalese, afraid of opaque fees, or simply unaware of their statutory protections under Indian law.

**Nyaya Sahayak (न्याय सहायक)** is a GenAI-powered legal literacy and assistance platform designed to bridge this divide. It translates complex legal agreements (rental deeds, employment contracts, consumer notices) and plain-text dispute narratives into **clear, structured, plain-language legal intelligence** in both **English and हिन्दी (Hindi)**.

> ⚠️ **Statutory Disclaimer**: *Nyaya Sahayak is a legal literacy and triage tool designed in compliance with Section 29 of the Advocates Act, 1961. It provides legal information, statutory grounding, and directions to legal aid forums — it does **not** provide formal legal advice or substitute for a licensed advocate.*

---

## 🌟 Key Capabilities & Innovation

```
   ┌────────────────────────────────────────────────────────┐
   │             User Input (Document or Text)              │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │     🛡️ Indian PII Redaction (Aadhaar, PAN, Phone)      │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │   💬 Adaptive Clarification Engine (Anti-Hallucinate)  │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │   🧠 Grounded RAG + Statutory Knowledge + Gemini AI    │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │  📊 Plain-Language Report • State Rights • Lawyer Brief│
   └────────────────────────────────────────────────────────┘
```

### 1. 🛡️ Pre-Ingestion Indian PII Redaction
Privacy is non-negotiable. Before any document text or description is analyzed or fed into the AI model, our high-speed regex & NER pipeline strips all sensitive Indian identity markers:
- `<AADHAAR>`: 12-digit UIDAI numbers
- `<PAN>`: 10-digit Income Tax Permanent Account Numbers
- `<PHONE>`: Indian mobile numbers (`+91` format supported)
- `<EMAIL>`: Personal email addresses
- `<CREDIT_CARD>`: Card numbers
- `<PERSON>`: Real person names via spaCy Named Entity Recognition

### 2. 💬 Adaptive Pre-Analysis Clarification Engine
Generic AI chatbots hallucinate because they make assumptions about missing facts. Nyaya Sahayak features an **interactive clarification step** that analyzes the initial submission and asks 1–3 essential questions (e.g., state jurisdiction, written receipts, timeline) before generating the final report.

### 3. ⚖️ Deterministic Risk Flagging & Clause Analysis
Automatically classifies clauses into **High**, **Medium**, and **Low Risk** based on Indian statutory rules:
- **Rental / Tenancy**: Arbitrary 100% deposit forfeiture, eviction without mandatory notice, illegal utility disconnection, and excessive rent escalation.
- **Employment**: Post-employment non-compete clauses (void under Section 27 of the Indian Contract Act, 1872), termination at will, and unfair IP assignment.
- **Consumer**: "No refund under any condition" clauses, unfair dispute jurisdiction, and voided warranties.

### 4. 🏛️ State-Specific "Know Your Rights" Explorer
Legal rights in India vary by state. The dedicated **Rights Explorer** allows citizens to select their state (e.g., Maharashtra, Delhi, Karnataka) and retrieve exact, curated statutory entitlements:
- **Maharashtra Rent Control Act, 1999**: Protection of essential services (Section 29), eviction restrictions (Section 16), standard rent guidelines, and rent receipt obligations.
- **Direct Legal Aid Links**: Eligibility categories and direct contact for **National Legal Services Authority (NALSA)**, **Maharashtra State Legal Services Authority (MSLSA)**, and District Legal Services Authorities (DLSA).

### 5. 🌐 Bilingual Inclusivity (English & हिन्दी)
Instant full-page toggle between English and Hindi allows citizens, families, and grassroots paralegals from non-English backgrounds to understand their rights seamlessly.

### 6. 📄 Lawyer-Prep Brief Generation
Empowers users to export a structured, court-ready **2-page Markdown/PDF brief** summarizing the facts, disputed clauses, applicable statutory sections, and evidence checklist before consulting a lawyer.

---

## 🛠️ Architecture & Tech Stack

### Frontend
- **Framework**: React 18 with TypeScript
- **Bundler**: Vite
- **Styling**: Tailored Dark-Mode Glassmorphism Design System (Accessible, high-contrast, responsive)
- **Internationalization**: Custom lightweight i18n engine (`en.json`, `hi.json`)

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Runtime**: Serverless-optimized execution (< 2.5s cold-start response time)
- **AI / LLM Engine**: Google GenAI SDK (`gemini-1.5-flash` / `gemini-2.5-flash`)
- **Knowledge Store**: In-Memory BM25-style statute similarity ranker with zero disk I/O latency
- **Document Extractors**: PyMuPDF (`fitz`), `python-docx`, and Pillow
- **Rate Limiting & Security**: SlowAPI with client IP tracking and strict CORS allow-lists

---

## 🚀 Live Demo & Deployment

| Environment | URL |
| :--- | :--- |
| **Production App (Vercel)** | [https://nayaya-sahayak.vercel.app](https://nayaya-sahayak.vercel.app) |
| **API Health Check** | [https://nayaya-sahayak.vercel.app/api/health](https://nayaya-sahayak.vercel.app/api/health) |

---

## 💻 Local Development Setup

### Prerequisites
- **Node.js**: v18.0 or higher
- **Python**: v3.11 or higher
- **Git**
- A **Google Gemini API Key** ([Get one for free at Google AI Studio](https://aistudio.google.com/))

### 1. Clone the Repository
```bash
git clone https://github.com/mayureshwadile28/Nayaya-Sahayak.git
cd Nayaya-Sahayak
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On macOS / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

Edit `backend/.env` with your credentials:
```ini
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
MAX_UPLOAD_SIZE=10485760
RATE_LIMIT_RPM=30
```

Start the backend server:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API docs will be available at `http://localhost:8000/docs`.

### 3. Frontend Setup
Open a new terminal window:
```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🧪 Testing & Code Quality

The codebase maintains a strict **100% test pass rate** with comprehensive unit and integration coverage.

```bash
# Run backend test suite (48 tests covering documents, extraction, RAG, and rights)
cd backend
python -m pytest tests/ -v

# Run code linter
python -m ruff check app tests

# Run frontend production build test
cd ../frontend
npm run build
```

---

## 📂 Project Structure

```text
Nayaya-Sahayak/
├── backend/
│   ├── app/
│   │   ├── config.py              # Pydantic settings with env sanitization
│   │   ├── main.py                # FastAPI app with CORS & rate limiting
│   │   ├── data/                  # Verified statutes & NALSA legal aid data
│   │   ├── models/                # Pydantic schemas & in-memory store
│   │   ├── routes/                # Documents, Rights, and Export endpoints
│   │   └── services/              # Gemini, Extraction, Redaction, Vector Store
│   ├── tests/                     # 48 Automated unit & integration tests
│   ├── main.py                    # Root entrypoint for Vercel Serverless
│   ├── pyproject.toml             # Python build configuration & dependencies
│   └── requirements.txt           # Pip dependencies
├── frontend/
│   ├── src/
│   │   ├── components/            # Nav, Footer, Language, ClarificationModal
│   │   ├── hooks/                 # Type-safe API client (useApi.ts)
│   │   ├── i18n/                  # English & Hindi translation catalogs
│   │   ├── pages/                 # Home, Upload, Analysis, Rights, Export
│   │   ├── types/                 # Strict TypeScript schemas
│   │   └── index.css              # Custom responsive design system
│   ├── package.json
│   └── vite.config.ts
├── vercel.json                    # Multi-service monorepo deployment config
└── README.md                      # Project documentation
```

---

## ⚖️ Legal & Ethical Compliance

Nyaya Sahayak is built with strict adherence to legal ethics:
1. **Section 29, Advocates Act, 1961**: The tool strictly provides information and plain-language summaries; it never claims to represent clients or issue binding legal advice.
2. **Statutory Grounding**: The AI reasoning is anchored against statutory ground truths including the **Model Tenancy Act**, **Consumer Protection Act, 2019**, **Indian Contract Act, 1872**, and state rent control acts.
3. **NALSA Access**: Actively routes economically disadvantaged citizens to free, government-authorized legal aid under the **Legal Services Authorities Act, 1987**.

---

## 🤝 Contributing

Contributions, feedback, and pull requests are welcome!
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

---

<div align="center">
  <b>Built with ❤️ for Citizen Legal Empowerment</b><br>
  <i>Nyaya Sahayak — Making Justice Accessible, One Document at a Time.</i>
</div>
