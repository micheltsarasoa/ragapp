FROM python:3.12-slim

WORKDIR /app

RUN pip install uv && apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

COPY . .

RUN mkdir -p uploads data

EXPOSE 8000 8501

# Default: run the API. Override in docker-compose for the UI.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
