
# Use pixi image as a parent image
FROM ghcr.io/prefix-dev/pixi:latest

# Set the working directory in the container
WORKDIR /app

# Copy the pixi configuration files
COPY pixi.toml pixi.lock ./

# Install project dependencies
# This will also install the python version specified in pixi.toml
RUN pixi install --frozen

# Copy the rest of the application code
COPY . .

# Download and cache the models
# The sentence-transformers library caches models in /root/.cache/torch/sentence_transformers/
# The transformers library caches models in /root/.cache/huggingface/hub/
RUN pixi run python download_models.py

# Argument for the token
ARG TOKEN

# Argument for the Institute URL
ARG INSTITUTE_URL
ENV INSTITUTE_URL=${INSTITUTE_URL}

# Create the settings.ini file
RUN mkdir -p campus_plan_bot/settings
RUN echo "[DEFAULT]" > campus_plan_bot/settings/settings.ini
RUN echo "token = ${TOKEN}" >> campus_plan_bot/settings/settings.ini

# Make port 8000 available to the world outside this container
EXPOSE 8000

ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1

# Run the app
CMD ["pixi", "run", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
