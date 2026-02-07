# HVAC Occupancy Forecasting - Development Environment
# Python data science image with Prophet, PyTorch, and ML libraries

FROM python:3.11-slim-bookworm

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set Python to run in unbuffered mode
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies required for data science libraries
# - build-essential: compiler tools for building Python packages
# - git: version control
# - libgomp1: OpenMP for parallel processing (used by Prophet, sklearn)
# - Additional libs for matplotlib and other visualization tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    libgomp1 \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install core data science packages
# These are installed in the base image for faster environment setup
RUN pip install --no-cache-dir \
    pandas>=2.0.0 \
    numpy>=1.24.0 \
    matplotlib>=3.7.0 \
    plotly>=5.15.0 \
    seaborn>=0.12.0 \
    scikit-learn>=1.3.0 \
    prophet>=1.1.4 \
    jupyter>=1.0.0 \
    ipykernel>=6.0.0 \
    python-dateutil>=2.8.0 \
    pytz>=2023.3 \
    tqdm>=4.65.0

# Install PyTorch CPU version separately (uses different index)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Set working directory
WORKDIR /workspace

# Default command
CMD ["/bin/bash"]
