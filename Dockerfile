FROM python:3.11-slim

WORKDIR /app

RUN pip install uv

COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

COPY . .

RUN mkdir -p uploads

EXPOSE 8000 8501

# Default: run the API. Override in docker-compose for the UI.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
