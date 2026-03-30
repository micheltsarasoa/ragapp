a project based on a video yt : https://www.youtube.com/watch?v=AUQJ9eeP-Ls

# Initialize project
> uv init .

## Requirements
> uv add fastapi inngest llama-index-core llama-index-readers-file python-dotenv qdrant-client uvicorn streamlit openai

## create env
OPENAI_API_KEY=

## create code inside main.py
> create functions
> make it available for uvicorn
> run : uv run uvicorn main:app
> will be available on :8000

## run dev server, connect the :8000 and control inngest server
> npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery



# Implement vector database

## create qdrant_storage folder
> 

1. Run locally qdrant in docker in our computer
> docker run -d --name qdrantRagDb -p 6333:6333 -v "$(pwd)/qdrant_storage:/qdrant/storage" 

2. create vector_db.py to able to connect into the vector docker db


# INNGEST = see inngest documentation, in inngest functions, steps


## invoke rag_app
>
```json
{
  "data": {
    "pdf_path": "C:\\Users\\jms\\OneDrive - SPC CONSULTANTS\\Applications\\Certificate of Analysis.pdf"
  }
}
```


# Querying vectorDb


# adding the frontend

## write steamlit script

## run 
> uv run streamlit run .\streamlit_app.py

# "aller plus loin" : to do next for testing
 - throttling
 - rate limit

 - See deploiment documentation in inngest to deploy in production
 - move openai key to grok api key