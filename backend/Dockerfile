# Use official Python image
FROM python:3.13-slim

# Prevent Python from buffering stdout
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies (including compiler tools needed to build Python packages
# with C extensions) and clean up apt cache to reduce image size
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt backend/requirements.txt

# Install Python deps
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy config
COPY backend/.env backend/.env

# Copy backend code
COPY backend/ backend/

# Copy frontend dist (build this locally first: cd frontend && npm run build)
COPY frontend/dist frontend/dist/

# Switch to backend directory
WORKDIR /app/backend

# Collect static files
# TODO: Consider moving collectstatic to the container startup via an entrypoint script, or use multi-stage builds where static files are collected separately.
RUN python manage.py collectstatic --noinput

# Expose Django dev server port
EXPOSE 8000

# TODO: Increase number of workers after validating app in production and once we get real traffic
# Run Django
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
CMD ["gunicorn", "music_recommendation.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "300", "--preload", "--access-logfile", "-", "--error-logfile", "-"]