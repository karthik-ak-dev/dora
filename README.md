# Dora 🧠

**Your AI-Powered Second Brain for Content**

Dora transforms your chaotic bookmark lists into an organized, searchable, and intelligent knowledge base. Stop losing great content in endless "Watch Later" playlists and forgotten "Saved" collections. Dora uses advanced AI to analyze, categorize, and cluster your saved content from Instagram, YouTube, and the web, making it useful and accessible when you need it.

---

## 🌟 Why Dora?

We all save content we want to revisit—recipes, travel tips, tutorials, or inspiration. But finding it later is a nightmare. Dora solves this by:

*   **Understanding Context**: It doesn't just save a link; it watches the video, reads the article, and understands what it's about.
*   **Auto-Organization**: No more manual tagging or folder management. Dora groups related content automatically.
*   **Instant Recall**: Find exactly what you're looking for with natural language search.

---

## 🚀 Key Features

### 📥 Smart Ingestion
Simply paste a URL, and Dora goes to work. It automatically extracts:
*   **Metadata**: Titles, descriptions, and authors.
*   **Transcripts**: Full text from YouTube videos and Instagram Reels.
*   **Visual Context**: AI analysis of the visual content in videos and images.

### 🧩 AI Clustering
Dora dynamically groups your content into meaningful "Clusters" based on semantic similarity.
*   *Example*: You save 5 different reels about cafes in Indiranagar. Dora automatically creates an **"Indiranagar Cafe Hopping"** cluster for you.
*   Clusters evolve as you save more content.

### 🔍 Semantic Search
Forget trying to remember the exact keyword. Search the way you think:
*   *"Show me healthy breakfast ideas with eggs"*
*   *"Python tutorials for beginners"*
*   *"Places to visit in Kyoto"*

### ⚡ Efficient & Scalable
*   **Global Deduplication**: Our `SharedContent` architecture ensures that if 1,000 users save the same viral video, we only process it once.
*   **Cost-Effective**: Smart resource management keeps AI costs low while delivering premium intelligence.

### 🔒 Private & Personalized
*   **Your Context**: Add your own notes and tags to any saved item.
*   **Private Clusters**: Your clusters are unique to your collection and interests.

---

## 🛠️ Technical Overview

Dora is built with a modern, scalable tech stack designed for high performance and AI integration.

*   **Backend**: Python 3.11+, FastAPI
*   **Database**: PostgreSQL (AWS Aurora Serverless v2)
*   **Vector Search**: Qdrant
*   **AI/ML**: OpenAI GPT-4o-mini (Analysis), `text-embedding-3-small` (Embeddings), Scikit-learn (Clustering)
*   **Infrastructure**: AWS ECS Fargate, Lambda, SQS

For detailed documentation on the architecture, data models, and API, please visit the [`docs/`](docs/) directory.

*   [**Core Entities**](docs/implementation-guide/core-entities.md)
*   [**API Reference**](docs/implementation-guide/api.md)
*   [**AI Pipelines**](docs/implementation-guide/03-ai-pipelines.md)

---

## ⚡ Getting Started

### Prerequisites
*   Python 3.11+
*   Docker & Docker Compose
*   OpenAI API Key

### Quick Start
1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/dora.git
    cd dora
    ```

2.  **Set up Environment Variables**
    ```bash
    cp .env.example .env
    # Edit .env with your DB credentials and API keys
    ```

3.  **Run with Docker Compose**
    ```bash
    docker-compose up -d --build
    ```

4.  **Access the API**
    *   API Docs: `http://localhost:8000/docs`
    *   Health Check: `http://localhost:8000/health`

---

## 📄 License

This project is licensed under the MIT License.