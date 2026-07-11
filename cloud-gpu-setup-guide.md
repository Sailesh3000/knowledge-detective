# AMD Cloud GPU Setup Guide & Next Steps

This document provides recommendations on choosing the right GPU Droplet for your AMD Hackathon project and outlines the steps to deploy your Qdrant, Neo4j, and backend containers.

## 1. Choosing Your GPU Plan

**Recommendation: `MI300X x1` ($1.99/hr)**
- **Why?** The MI300X x8 ($15.92/hr) will burn through your $100 credits in just over 6 hours. The single MI300X gives you a massive 192GB of VRAM and will last you for **~50 hours**, which is more than enough to get you through tonight and the rest of the hackathon. 
- 192GB VRAM is incredibly powerful and easily handles Qdrant, Neo4j, and running high-end LLM/Embedding models on the side.

## 2. Choosing Your Image

**Recommendation: `PyTorch Quick Start Package`**
- **Why?** Since you are building an AI/knowledge app (`embedder.py` implies you're doing ML embeddings), PyTorch is the industry standard for loading custom models. This package comes pre-installed with Ubuntu 24.04, AMD ROCm 7.2.4 drivers, Python, Docker, and JupyterLab. It saves you the headache of manually installing GPU drivers.
- *Alternative:* If you know you strictly want to serve an LLM (like Llama 3) via an API, you could select the **vLLM Quick Start**. But PyTorch is safer and more flexible for general hacking.

## 3. SSH Key Setup
Before creating the droplet, you **must** add an SSH key.
1. On your local Windows machine, open PowerShell or Command Prompt.
2. Run `ssh-keygen -t rsa -b 4096` (press Enter to accept default locations).
3. Open the public key file by running: `cat ~/.ssh/id_rsa.pub`
4. Copy the entire output and paste it into the "Add an SSH Key" section in the AMD Developer Cloud console.

---

## 4. Next Steps After Droplet Creation

Once your droplet says "Running" and gives you an IP address, follow these steps to migrate your stack:

### Step 1: Connect to Your GPU Droplet
In your local terminal, SSH into the new server:
```bash
ssh root@<YOUR_DROPLET_IP_ADDRESS>
```

### Step 2: Clone Your Repository to the Cloud
Once inside the droplet, you need to bring your code over. (Make sure your latest code is pushed to GitHub):
```bash
git clone <YOUR_GITHUB_REPO_URL>
cd knowledge-detective
```

### Step 3: Run Your Services using Docker Compose
Your repository already has a `docker-compose.yml` that configures Qdrant, Neo4j, and your Backend.
Start everything in detached mode:
```bash
docker compose up -d
```
Docker will automatically pull the Qdrant and Neo4j images and build your backend.

### Step 4: Validate Services are Running
Check that the containers are healthy:
```bash
docker ps
```
You should see:
- `qdrant` on port `6333`
- `neo4j` on ports `7474`, `7687`
- `backend` on port `8080`

### Step 5: Update Local Configuration (If needed)
If you still want to run some code locally (e.g., your frontend) but connect to the cloud databases, you will need to update your local `.env` or `config.py` to point to the remote IP instead of localhost:
- **Qdrant URL:** `http://<YOUR_DROPLET_IP_ADDRESS>:6333`
- **Neo4j URI:** `bolt://<YOUR_DROPLET_IP_ADDRESS>:7687`
- **Backend API:** `http://<YOUR_DROPLET_IP_ADDRESS>:8080`

### Step 6: Connect Ollama or Local LLMs
Your docker-compose currently looks for an LLM at `OLLAMA_BASE_URL=http://host.docker.internal:11434`. 
Since you now have an incredibly powerful 192GB VRAM GPU in the cloud:
1. You can install Ollama directly on the droplet: `curl -fsSL https://ollama.com/install.sh | sh`
2. Start a heavy model that wouldn't normally fit on a laptop: `ollama run llama3.1:70b`
3. Update your `docker-compose.yml` to point `OLLAMA_BASE_URL` to `http://localhost:11434` (since Ollama is now running natively on the same cloud server).
