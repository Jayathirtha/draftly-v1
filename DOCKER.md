# Draftly Docker Setup

## Quick Start

### Option 1: Using Docker Compose (Recommended)

1. **Set up environment variables**:
   ```bash
   # Copy your .env file or create one with:
   GROQ_API_KEY=your_groq_api_key
   DATABASE_URL=postgresql://postgres:password@draftly-db:5432/draftly
   ```

2. **Build and run**:
   ```bash
   docker-compose up -d
   ```

3. **Access the application**:
   - Frontend: http://localhost:8000/ui
   - API Docs: http://localhost:8000/docs

4. **Stop the application**:
   ```bash
   docker-compose down
   ```

### Option 2: Using Docker Only

1. **Build the image**:
   ```bash
   docker build -t draftly:latest .
   ```

2. **Run the container**:
   ```bash
   docker run -d \
     --name draftly-app \
     -p 8000:8000 \
     -e GROQ_API_KEY=your_groq_api_key \
     -e DATABASE_URL=postgresql://user:pass@host:5432/draftly \
     -v $(pwd)/resources:/app/resources:ro \
     -v $(pwd)/.env:/app/.env:ro \
     draftly:latest
   ```

## Sharing Your Image

### Push to Docker Hub

1. **Tag your image**:
   ```bash
   docker tag draftly:latest your-dockerhub-username/draftly:latest
   ```

2. **Login to Docker Hub**:
   ```bash
   docker login
   ```

3. **Push the image**:
   ```bash
   docker push your-dockerhub-username/draftly:latest
   ```

### Share Image as File

1. **Save image to tar file**:
   ```bash
   docker save draftly:latest -o draftly-image.tar
   ```

2. **Compress (optional)**:
   ```bash
   gzip draftly-image.tar
   ```

3. **Load image on another machine**:
   ```bash
   docker load -i draftly-image.tar
   # or if compressed:
   docker load -i draftly-image.tar.gz
   ```

## Environment Variables

Required:
- `GROQ_API_KEY`: Your Groq API key
- `DATABASE_URL`: PostgreSQL connection string

Optional:
- `GROQ_MODEL_NAME`: Groq model to use (default: llama-3.3-70b-versatile)
- `GMAIL_SCOPES`: Gmail API scopes (default: auth/gmail.modify,auth/gmail.readonly,...)

## Notes

- Make sure your `resources/` folder contains the Google OAuth client secrets JSON file
- The application runs on port 8000 by default
- PostgreSQL data is persisted in a Docker volume when using docker-compose
- For production, update CORS settings and security configurations
