# vibe-coding-hackathon-2026-zenithx
Hackathon team repository for ZenithX - [hackindia-team:vibe-coding-hackathon-2026:zenithx]
# 🇮🇳 Sarkar Setu — AI Government Scheme Finder

> AI-powered, voice-first platform that helps rural Indians find eligible 
> government schemes in simple Hindi with nearby Jan Seva Kendra on map.

---



---

##  Problem Statement

Millions of Indians, especially in rural areas, are unaware of government 
welfare schemes they are eligible for — due to language barriers, lack of 
personalized guidance, and no knowledge of nearby service centers. Existing 
portals are English-heavy, text-only, and require manual searching with no AI 
assistance. Sarkar Setu solves this by providing a voice-first, Hindi-language 
AI platform that identifies eligible schemes, explains them in simple Hindi, 
answers voice questions in real time, and shows nearby Jan Seva Kendra on map.

---

##  Features

- 🔍 Scheme eligibility based on category, state and income
- 🤖 AI explanation in Hindi using Groq LLaMA 3.3 70B
- 🎤 Voice Q&A — ask questions about schemes by speaking
- 🗺️ Interactive map of nearby Jan Seva Kendra (2km radius)
- 🔊 Automatic voice narration of nearest service center
- 📊 Analytics dashboard for admin
- 👤 Face recognition login

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python Flask |
| Database | MongoDB |
| AI | Groq API (LLaMA 3.3 70B) |
| Frontend | HTML, CSS, JavaScript |

| Voice | Web Speech API |
| Face | OpenCV |

---


## ⚙️ Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/HackIndiaXYZ/vibe-coding-hackathon-2026-zenithx.git
cd vibe-coding-hackathon-2026-zenithx
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup environment variables
```bash
cp .env.example .env
```
Keys are already filled in .env.example — no changes needed.

### 4. Make sure MongoDB is running
```bash
# MongoDB should be running on localhost:27017
# If not, start it from Services or run:
mongod
```

### 5. Import sample data
```bash
mongoimport --db sarkarsetu --collection schemes --file data/schemes.json --jsonArray
mongoimport --db sarkar_setu --collection analytics --file data/analytics.json --jsonArray
```

### 6. Run the app
```bash
python app.py
```

### 7. Open in browser
