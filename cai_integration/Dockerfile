# Dockerfile for Open-WebUI Custom CML Runtime

FROM docker.repository.cloudera.com/cloudera/cdsw/ml-runtime-pbj-jupyterlab-python3.11-standard:2025.09.1-b5

# Install system dependencies
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and npm
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
RUN apt-get install -y nodejs

# Copy project files
COPY . /home/cdsw/

# Install Python dependencies
RUN pip install uv
RUN uv venv /home/cdsw/.venv
ENV PATH="/home/cdsw/.venv/bin:$PATH"
RUN uv pip install -e /home/cdsw/backend

# Install frontend dependencies and build
RUN npm install --force --prefix /home/cdsw
RUN npm run build --prefix /home/cdsw

# Switch back to the default user
USER cdsw

# Set the working directory
WORKDIR /home/cdsw
