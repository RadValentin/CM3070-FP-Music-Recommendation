# Use official Python image
FROM python:3.13-slim

# Prevent Python from buffering stdout
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt backend/

# Install Python deps
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code
COPY backend/ backend/

# Copy frontend dist (build this locally first: cd frontend && npm run build)
COPY frontend/dist frontend/dist/

# Switch to backend directory
WORKDIR /app/backend

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose Django dev server port
EXPOSE 8000

# Run Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]