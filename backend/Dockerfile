# The "recipe" for the backend lunchbox.
# Each line is a step; Docker caches steps so rebuilds are fast.

# Start from an official image that already has Python 3.12 installed.
FROM python:3.12-slim

# Everything from here on happens inside /app in the container.
WORKDIR /app

# Copy ONLY the requirements file first, then install.
# Trick: if requirements.txt hasn't changed, Docker reuses the cached
# install step even when your code changes -- much faster rebuilds.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the source code.
COPY . .

# Documentation of which "door" the app listens on.
EXPOSE 8000

# Default startup command (docker-compose overrides this in dev to add --reload).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
