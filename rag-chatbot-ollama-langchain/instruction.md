## Build End-to-End RAG Chatbot with Ollama and LangChain

Build a Retrieval-Augmented Generation (RAG) chatbot using Ollama (CPU mode) and LangChain that answers domain-specific questions from custom PDF documents, exposed as a Flask REST API with a chat UI and Docker orchestration.

### Technical Requirements

- Language: Python 3.x
- Working directory: `/app`
- Key dependencies: `langchain`, `langchain-community`, `langchain-ollama`, `pypdf`, `chromadb`, `sentence-transformers`, `flask`
- All dependency requirements must be listed in `/app/requirements.txt`

### Project Structure

The project must contain at minimum the following files:

```
/app/
├── requirements.txt
├── ingest.py
├── rag_chain.py
├── app.py
├── templates/
│   └── index.html
├── docker-compose.yml
├── Dockerfile
└── README.md
```

### Component Specifications

#### 1. Document Ingestion (`/app/ingest.py`)

This module handles loading PDFs, splitting them into chunks, and indexing into a vector store.

- Must define a function `load_and_split(pdf_path: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list` that:
  - Accepts a path to a PDF file
  - Splits the document into text chunks using LangChain's `RecursiveCharacterTextSplitter` with the given `chunk_size` and `chunk_overlap`
  - Returns a list of LangChain `Document` objects, each having `.page_content` (str) and `.metadata` (dict containing at least `"source"` with the original file path)

- Must define a function `build_vectorstore(documents: list, persist_directory: str = "./chroma_db") -> object` that:
  - Accepts the list of Document objects from `load_and_split`
  - Uses `sentence-transformers/all-MiniLM-L6-v2` as the embedding model via LangChain's `HuggingFaceEmbeddings`
  - Creates and persists a ChromaDB vector store at the given `persist_directory`
  - Returns the Chroma vector store object

- When run as `__main__`, the script should accept a PDF path as a command-line argument (`sys.argv[1]`), call `load_and_split` then `build_vectorstore`, and print the number of chunks indexed to stdout in the format: `Indexed {N} chunks from {pdf_path}`

#### 2. RAG Chain (`/app/rag_chain.py`)

This module implements the LangChain RAG pipeline.

- Must define a function `get_retriever(persist_directory: str = "./chroma_db", k: int = 3) -> object` that:
  - Loads the persisted ChromaDB vector store from `persist_directory` using the same `all-MiniLM-L6-v2` embeddings
  - Returns a LangChain retriever configured to return `k` results

- Must define a function `build_rag_chain(retriever, model_name: str = "llama3.2:3b") -> object` that:
  - Creates an Ollama LLM instance via `langchain_ollama.ChatOllama` with the given `model_name`
  - Constructs a prompt template that includes a `{context}` variable for retrieved passages and a `{question}` variable for the user query
  - Assembles and returns a LangChain chain (using LCEL or `RetrievalQA`) that: retrieves context → formats prompt → calls LLM → parses output

- Must define a function `query(chain, question: str) -> dict` that:
  - Invokes the chain with the given question
  - Returns a dict with keys `"answer"` (str) and `"sources"` (list of str, each being the `source` metadata from retrieved documents)

#### 3. Flask Application (`/app/app.py`)

- The Flask app must serve on `0.0.0.0:5000`
- Must expose a `POST /ask` endpoint that:
  - Accepts JSON body: `{"question": "some question"}`
  - Returns JSON response: `{"answer": "...", "sources": ["source1.pdf", ...]}`
  - Returns HTTP 400 with JSON `{"error": "..."}` if `question` field is missing or empty
- Must serve the static chat UI at `GET /` by rendering `/app/templates/index.html`
- The Flask app object must be named `app` (i.e., `app = Flask(__name__)`)

#### 4. Chat UI (`/app/templates/index.html`)

- A single-page HTML file with embedded CSS and JavaScript
- Must contain an input field for the user question and a submit/send button
- Must send requests to the `/ask` endpoint via `fetch` or `XMLHttpRequest` with `Content-Type: application/json`
- Must display the returned answer text and the list of source documents on the page

#### 5. Docker Compose (`/app/docker-compose.yml`)

- Must define at least two services:
  - `ollama`: using the `ollama/ollama` image, exposing port `11434`
  - `app` (or `web`): the Flask application, built from `/app/Dockerfile`, exposing port `5000`, depending on the `ollama` service
- Must define a shared named volume (e.g., `chroma_data`) mounted in the app service for the vector store persistence directory

#### 6. Dockerfile (`/app/Dockerfile`)

- Must use a Python base image (e.g., `python:3.11-slim`)
- Must copy `requirements.txt` and install dependencies
- Must copy application source code
- Must set the default command to run the Flask app (e.g., via `gunicorn` or `python app.py`)
- Must expose port `5000`

#### 7. README (`/app/README.md`)

- Must include:
  - A quick-start section with steps to build and run via Docker Compose
  - A curl example demonstrating the `/ask` endpoint, e.g.: `curl -X POST http://localhost:5000/ask -H "Content-Type: application/json" -d '{"question": "What is..."}'`
  - Instructions for ingesting PDF documents before chatting

### requirements.txt

Must include at minimum these packages (exact versions not required):
- `langchain`
- `langchain-community`
- `langchain-ollama`
- `pypdf`
- `chromadb`
- `sentence-transformers`
- `flask`
