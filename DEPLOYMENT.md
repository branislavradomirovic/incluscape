# Railway Deployment Guide

This guide explains how to deploy INCLUSCAPE to Railway with both Streamlit and Ollama running in the cloud.

## Prerequisites

1. **Railway Account**: Sign up at https://railway.app (free tier available)
2. **GitHub Account**: Your repo pushed to GitHub
3. **Railway CLI** (optional): `npm install -g @railway/cli`

## Deployment Options

### Option A: Deploy via Railway Dashboard (Easiest, No CLI Required)

#### Step 1: Push Code to GitHub
```bash
git add Dockerfile docker-compose.yml railway.toml .dockerignore
git commit -m "Add Railway deployment configuration"
git push origin main
```

#### Step 2: Create Railway Project
1. Go to [railway.app](https://railway.app)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Authorize Railway and select your `incluscape` repository
5. Click **"Deploy"**

#### Step 3: Configure Services

Railway will automatically detect the Dockerfile and create one service. Now add Ollama as a separate service:

1. In your Railway project dashboard, click **"+ New Service"**
2. Select **"Add from Marketplace"**
3. Search for and select **"Ollama"** (if available)
   - **Alternative**: Select "Docker Image" and use `ollama/ollama:latest`
4. Configure Ollama service:
   - Port: `11434`
   - Set environment variable: `OLLAMA_NUM_GPU=-1` (enable GPU acceleration if available)

#### Step 4: Connect Services & Set Environment Variables

1. Click your Streamlit service
2. Go to **Variables** tab
3. Add the following environment variables from `RAILWAY_ENV.example`:
   ```
   OLLAMA_BASE_URL=http://ollama:11434
   OLLAMA_MODEL=qwen2.5:14b-instruct
   OLLAMA_TIMEOUT_SEC=600
   OLLAMA_KEEP_ALIVE=60m
   OLLAMA_NUM_CTX=4096
   OLLAMA_NUM_GPU=-1
   OLLAMA_NUM_BATCH=512
   ENABLE_SEMANTIC_ANALYSIS=true
   DATABASE_PATH=./data/incluscape.db
   LOG_LEVEL=INFO
   DEBUG=false
   ```

4. Generate a strong `SECRET_KEY` and add it:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

5. Click **Deploy** to apply changes

#### Step 5: Verify Deployment

1. Go to the **Deployments** tab to monitor build progress
2. Once deployed, click the **Public URL** to access your app
3. First load may take 30-60 seconds (Ollama model initialization)

---

### Option B: Deploy via Railway CLI

#### Step 1: Install Railway CLI
```bash
npm install -g @railway/cli
```

#### Step 2: Login & Link Project
```bash
railway login
railway link --projectId your-railway-project-id
```

#### Step 3: Configure Services
```bash
# Deploy main service
railway up

# Create Ollama service
railway service add ollama/ollama:latest
```

#### Step 4: Set Environment Variables
```bash
railway variable set OLLAMA_BASE_URL=http://ollama:11434
railway variable set OLLAMA_MODEL=qwen2.5:14b-instruct
# ... add other variables from RAILWAY_ENV.example
```

#### Step 5: Deploy
```bash
railway up --detach
```

---

## Important Notes

### Model Initialization
When Ollama starts for the first time on Railway, it will download the qwen2.5:14b-instruct model (~10-15 GB). This may take:
- **Upload time**: 5-30 minutes (depends on Railway's bandwidth)
- **Loading time**: 2-5 minutes per request (on first pull)

After initialization, inference will be fast (6-8 seconds per request).

### Railway Free Tier Limits
- **Compute**: Limited CPU/RAM (good for testing/light use)
- **Storage**: Keep database backups
- **Bandwidth**: Monthly limits apply
- **Sleeping**: Services may sleep after inactivity (paid plan prevents this)

### Persistent Storage
Your SQLite database and uploaded files are stored in Railway's ephemeral storage (lost on redeploy). To persist data:

1. Add Railway PostgreSQL service as database backend (instead of SQLite)
2. Or configure S3 for file uploads/exports

### Local Development
Test locally with Docker Compose before deploying:
```bash
docker-compose up -d
# App will be at http://localhost:8501
# Ollama will be at http://localhost:11434
```

---

## Troubleshooting

### "Ollama service unavailable"
- Check Ollama service is running: Click Ollama service → Logs tab
- Verify `OLLAMA_BASE_URL` matches the Ollama service name in Railway
- Wait 2-3 minutes for Ollama to fully initialize

### "Port already in use"
- Railway auto-assigns ports; don't hardcode port numbers in environment

### "Out of memory"
- Ollama 14B requires ~10GB RAM
- Streamlit may need 1-2GB
- Consider upgrading Railway plan or using smaller model (7B variant)

### "Build fails"
- Check build logs in Railway dashboard → Deployments tab
- Ensure `requirements.txt` is up to date: `pip freeze > requirements.txt`
- Verify Dockerfile path is correct: `./Dockerfile`

---

## Monitoring

### View Logs
```bash
# CLI: View logs in real-time
railway logs --follow

# Dashboard: Click service → Logs tab
```

### Health Checks
- **Streamlit health**: `GET /_stcore/health` (returns 200 when ready)
- **Ollama health**: `GET /api/tags` (returns model list when ready)

---

## Next Steps

1. **Database**: Migrate from SQLite to PostgreSQL (Railway offers free PostgreSQL tier)
2. **File Storage**: Configure S3 bucket for persistent uploads/exports
3. **Environment Secrets**: Use Railway's secret variables for API keys (Gemini, etc.)
4. **Custom Domain**: Add your own domain via Railway settings
5. **Monitoring**: Set up alerts for deployment failures

---

## Support

- **Railway Docs**: https://docs.railway.app
- **Railway Community**: https://railway.app/chat
- **Issue Tracker**: Report issues in the GitHub repository
