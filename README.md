# ASFATES — Automated Student Feedback Analysis System

Local Streamlit dashboard for cleaning, classifying, and summarizing campus event feedback using Groq LLM inference.

## Setup & Installation

### 1. Download the Project
Clone the repository (or click **Code → Download ZIP** on GitHub and extract it):
```bash
git clone [https://github.com/Shiyaban/ASFATES-.git](https://github.com/Shiyaban/ASFATES-.git)
cd ASFATES-
```

### 2. Create a Virtual Environment & Install Libraries
Open a terminal inside the `ASFATES-` folder and run:

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Add Your Groq API Key (`.env`)
1. Get a free API key from **GroqCloud** (note: *Groq* with a **q**, not Grok) at [console.groq.com/keys](https://console.groq.com/keys) — click **Create API Key** and copy it immediately (or paste the key shared privately in our group chat).
2. In the root `ASFATES-` folder (same level as `ASFATES.py`), create a new file named **`.env`** (no filename before the dot, no `.txt` extension).
3. Add this single line inside `.env` and save:
   ```env
   GROQ_API_KEY=gsk_paste_your_actual_key_here
   ```

### 4. Run the App
With your virtual environment active, start Streamlit:
```bash
python -m streamlit run ASFATES.py
```
Your browser will open automatically to `http://localhost:8501`. Upload a `.csv`/`.xlsx` file or switch to **Direct Live Insertion** to verify everything runs.