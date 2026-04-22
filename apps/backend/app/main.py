import inngest.fast_api
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import db
from app.inngest_functions.client import inngest_client
from app.inngest_functions.ingest_pdf import rag_ingest_pdf
from app.inngest_functions.query_pdf import rag_query_pdf_ai
from app.routes import auth, documents, llm_config, query

db.init_db()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:80", "http://localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(llm_config.router)

inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query_pdf_ai])
