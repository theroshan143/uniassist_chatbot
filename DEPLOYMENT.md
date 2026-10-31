# UniAssist: Cloud Deployment Guide

> **Production deployment instructions for UniAssist AI-Powered University Chatbot.**  
> Supports **Render**, **Hugging Face Spaces**, **Railway**, and **Docker**.

---

## 🚀 1. Is the Project Deployable?

**YES, 100% Deployable.**

UniAssist is architected as an asynchronous Python/FastAPI micro-monolith:
- **Zero Heavy External Daemons:** Uses embedded ChromaDB and SQLite (`uniassist.db`), requiring no external database clusters.
- **Auto-Boot Ingestion:** Automatically ingests and indexes all 12 policy handbooks on first boot if the vector store is empty.
- **Dynamic Port Binding:** Binds dynamically to cloud-assigned `$PORT` environment variables (`0.0.0.0:$PORT`).
- **Resilient Fallback:** Provides grounded vector synthesis fallback even if cloud LLM APIs experience rate limits.
- **Embedded Frontend:** The static frontend (`static/`) is served directly by FastAPI without needing a separate Node.js server.

---

## 🌐 2. Which Platform Should You Deploy On?

| Platform | Tier | Best For | Pros | Link |
|---|---|---|---|---|
| **Render.com** ⭐ *(Recommended)* | **Free** | Academic Submissions, Live Expo Demos | • Free public HTTPS URL (`https://uniassist.onrender.com`)<br>• Direct GitHub repository link<br>• Zero configuration via `render.yaml` | [render.com](https://render.com) |
| **Hugging Face Spaces** | **Free** | AI/ML Portfolio & Research | • Free Docker container hosting<br>• 16 GB RAM CPU tier<br>• Excellent credibility for AI evaluators | [huggingface.co](https://huggingface.co) |
| **Railway.app** | Free Trial | Multi-Service & Persistent Storage | • Easy Dockerfile deployment<br>• Supports persistent disk volumes for SQLite/ChromaDB | [railway.app](https://railway.app) |
| **Docker (Self-Hosted)** | Free | Local evaluation / VPS | • 100% isolated reproducible environment | Local |

---

## 🛠️ 3. What Is Needed Before Deployment?

1. **A GitHub Account & Repository:**
   - Push your `uniassist` folder to a GitHub repository (public or private).
2. **A Free Google AI Studio / Gemini API Key:**
   - Obtain from [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).
3. **Environment Variables to Set in Cloud Dashboard:**
   - `XAI_BASE_URL`: `https://generativelanguage.googleapis.com/v1beta/openai/`
   - `XAI_API_KEY`: `your_gemini_api_key_here`
   - `XAI_MODEL`: `gemini-3.8-flash`
   - `ADMIN_PASSWORD`: `admin123` (or your chosen secure password)
   - `DEMO_MODE`: `false`

---

## 📋 4. Step-by-Step Deployment Instructions

### Option A: Deploy on Render.com (Recommended — 5 Minutes)

1. **Push code to GitHub:**
   ```bash
   cd "C:\Users\kumar\AI CHATBOT\uniassist"
   git init
   git add .
   git commit -m "UniAssist initial release"
   git branch -M main
   git remote add origin https://github.com/<your-username>/uniassist.git
   git push -u origin main
   ```

2. **Create Web Service on Render:**
   - Go to [dashboard.render.com](https://dashboard.render.com/) and click **"New +"** $\rightarrow$ **"Web Service"**.
   - Select **"Build and deploy from a Git repository"** and select your `uniassist` repository.

3. **Configure Settings:**
   - **Name:** `uniassist-student-support`
   - **Region:** Singapore / Frankfurt / Oregon (closest to you)
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`

4. **Add Environment Variables (under Advanced $\rightarrow$ Environment Variables):**
   | Key | Value |
   |---|---|
   | `PYTHON_VERSION` | `3.11.9` |
   | `XAI_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta/openai/` |
   | `XAI_API_KEY` | *(Your Gemini API Key)* |
   | `XAI_MODEL` | `gemini-3.8-flash` |
   | `ADMIN_PASSWORD` | `admin123` |
   | `DEMO_MODE` | `false` |

5. **Click "Create Web Service":**
   - Render will build the dependencies, launch the server, automatically ingest the 12 knowledge documents into ChromaDB, and provide a live public HTTPS URL:
   - **Public URL:** `https://uniassist-student-support.onrender.com`
   - **Admin Dashboard:** `https://uniassist-student-support.onrender.com/admin`
   - **Swagger Docs:** `https://uniassist-student-support.onrender.com/docs`

---

### Option B: Deploy on Hugging Face Spaces (Docker — Free 16GB)

1. Create a free account at [huggingface.co](https://huggingface.co/).
2. Click your profile icon $\rightarrow$ **"New Space"**.
3. Set **Space Name**: `uniassist-chatbot`.
4. Select **Space SDK**: **Docker** $\rightarrow$ **Blank**.
5. Set Visibility: **Public**.
6. In **Settings $\rightarrow$ Variables and Secrets**, add your Secret:
   - Name: `XAI_API_KEY`
   - Value: *(Your Gemini API Key)*
7. Push your repository to the Hugging Face Space Git URL:
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/uniassist-chatbot
   git push space main
   ```
8. The Space builds automatically using the included `Dockerfile` and presents your live chatbot directly inside Hugging Face!

---

### Option C: Run Locally via Docker

If an evaluator wants to run the project in a containerized environment:

```bash
# 1. Build the Docker image
docker build -t uniassist:latest .

# 2. Run the container
docker run -d -p 8000:8000 --env-file .env --name uniassist-app uniassist:latest

# 3. Test the container
curl http://localhost:8000/health
```

---

## 🔒 5. Post-Deployment Verification Checklist

Once deployed, verify these 4 live endpoints:
- [ ] **Home Page:** `https://your-app-url/` loads the "Ask First" interface.
- [ ] **Health Endpoint:** `https://your-app-url/health` returns `{"status": "healthy", "knowledge_base_chunks": 100}`.
- [ ] **Live Query:** Ask *"What is the tuition fee for B.Tech CSE?"* and verify that it returns official citations.
- [ ] **Admin Portal:** `https://your-app-url/admin` accepts `admin123` and displays real-time analytics.

