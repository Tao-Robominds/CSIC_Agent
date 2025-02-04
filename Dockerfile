FROM continuumio/miniconda3

LABEL maintainer="joe.zhouanan@gmail.com"

# Set working directory
COPY . /app
WORKDIR /app

# Create and activate fastapi environment with your current Python version
RUN conda create --name fastapi python=3.12 -y  # adjust Python version to match your current env
RUN conda run -n fastapi pip install -r requirements.txt 
RUN conda clean --all -f -y

# Expose FastAPI default port
EXPOSE 8000

# Start FastAPI service
ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "fastapi", "pytest"]  # Changed to run tests
