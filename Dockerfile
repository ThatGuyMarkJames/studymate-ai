# Use a slim Python image to save space
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Set working directory
WORKDIR /app

# Install system dependencies (needed for some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 1. Install CPU-only PyTorch first (This is the huge space-saver!)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 2. Install Sentence-Transformers and other dependencies
# We use --no-cache-dir to avoid storing temporary install files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy the rest of the application code
COPY . .

# 4. Create uploads directory
RUN mkdir -p uploads/vectors

# 5. Expose the port
EXPOSE 8000

# 6. Start the application
CMD ["python", "-m", "backend.main"]

