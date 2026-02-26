FROM python:3.11-bookworm
WORKDIR /app
COPY requirements.txt ./
RUN apt-get update \
 && apt-get install -y --fix-missing libgpiod-dev python3-gpiozero \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
COPY agent.py .
CMD ["python", "agent.py"]
