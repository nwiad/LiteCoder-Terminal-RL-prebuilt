"""
Tests for RAG Chatbot with Ollama and LangChain.

Validates file existence, structure, content, function signatures,
Flask API configuration, Docker setup, and documentation.
Does NOT require a running Ollama instance — focuses on static analysis
and structural correctness.
"""

import os
import ast
import sys
import re

APP_DIR = "/app"


# ============================================================================
# Helper utilities
# ============================================================================

def read_file(rel_path):
    """Read a file relative to APP_DIR, return contents or None."""
    full = os.path.join(APP_DIR, rel_path)
    if not os.path.isfile(full):
        return None
    with open(full, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def parse_ast(rel_path):
    """Parse a Python file and return its AST, or None on failure."""
    src = read_file(rel_path)
    if src is None:
        return None
    try:
        return ast.parse(src)
    except SyntaxError:
        return None


def get_function_defs(tree):
    """Return a dict of {func_name: ast.FunctionDef} from top-level functions."""
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def get_func_arg_names(func_node):
    """Return list of argument names for a function node."""
    return [arg.arg for arg in func_node.args.args]


# ============================================================================
# 1. File existence tests
# ============================================================================

class TestFileExistence:
    """All required project files must exist."""

    def test_requirements_txt(self):
        assert os.path.isfile(os.path.join(APP_DIR, "requirements.txt")), \
            "requirements.txt not found"

    def test_ingest_py(self):
        assert os.path.isfile(os.path.join(APP_DIR, "ingest.py")), \
            "ingest.py not found"

    def test_rag_chain_py(self):
        assert os.path.isfile(os.path.join(APP_DIR, "rag_chain.py")), \
            "rag_chain.py not found"

    def test_app_py(self):
        assert os.path.isfile(os.path.join(APP_DIR, "app.py")), \
            "app.py not found"

    def test_index_html(self):
        assert os.path.isfile(os.path.join(APP_DIR, "templates", "index.html")), \
            "templates/index.html not found"

    def test_docker_compose(self):
        assert os.path.isfile(os.path.join(APP_DIR, "docker-compose.yml")), \
            "docker-compose.yml not found"

    def test_dockerfile(self):
        assert os.path.isfile(os.path.join(APP_DIR, "Dockerfile")), \
            "Dockerfile not found"

    def test_readme(self):
        assert os.path.isfile(os.path.join(APP_DIR, "README.md")), \
            "README.md not found"


# ============================================================================
# 2. requirements.txt tests
# ============================================================================

class TestRequirements:
    """requirements.txt must list all required packages."""

    REQUIRED_PACKAGES = [
        "langchain",
        "langchain-community",
        "langchain-ollama",
        "pypdf",
        "chromadb",
        "sentence-transformers",
        "flask",
    ]

    def _get_package_names(self):
        content = read_file("requirements.txt")
        assert content is not None, "requirements.txt missing"
        assert content.strip(), "requirements.txt is empty"
        # Normalize: strip version specifiers, lowercase, strip whitespace
        names = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Remove version specifiers like ==1.0, >=2.0, etc.
            pkg = re.split(r"[><=!~;@\[]", line)[0].strip().lower()
            if pkg:
                names.append(pkg)
        return names

    def test_all_required_packages_present(self):
        names = self._get_package_names()
        for pkg in self.REQUIRED_PACKAGES:
            assert pkg.lower() in names, \
                f"Required package '{pkg}' not found in requirements.txt"

    def test_not_empty(self):
        names = self._get_package_names()
        assert len(names) >= len(self.REQUIRED_PACKAGES), \
            "requirements.txt has fewer packages than required"


# ============================================================================
# 3. ingest.py tests — structure and function signatures
# ============================================================================

class TestIngestPy:
    """ingest.py must define load_and_split and build_vectorstore."""

    def test_syntax_valid(self):
        tree = parse_ast("ingest.py")
        assert tree is not None, "ingest.py has syntax errors or is missing"

    def test_load_and_split_exists(self):
        tree = parse_ast("ingest.py")
        assert tree is not None
        funcs = get_function_defs(tree)
        assert "load_and_split" in funcs, \
            "Function 'load_and_split' not found in ingest.py"

    def test_load_and_split_params(self):
        tree = parse_ast("ingest.py")
        assert tree is not None
        funcs = get_function_defs(tree)
        assert "load_and_split" in funcs
        args = get_func_arg_names(funcs["load_and_split"])
        assert "pdf_path" in args, \
            "load_and_split must accept 'pdf_path' parameter"

    def test_load_and_split_has_chunk_params(self):
        tree = parse_ast("ingest.py")
        assert tree is not None
        funcs = get_function_defs(tree)
        fn = funcs.get("load_and_split")
        assert fn is not None
        args = get_func_arg_names(fn)
        assert "chunk_size" in args, \
            "load_and_split must accept 'chunk_size' parameter"
        assert "chunk_overlap" in args, \
            "load_and_split must accept 'chunk_overlap' parameter"

    def test_build_vectorstore_exists(self):
        tree = parse_ast("ingest.py")
        assert tree is not None
        funcs = get_function_defs(tree)
        assert "build_vectorstore" in funcs, \
            "Function 'build_vectorstore' not found in ingest.py"

    def test_build_vectorstore_params(self):
        tree = parse_ast("ingest.py")
        assert tree is not None
        funcs = get_function_defs(tree)
        fn = funcs.get("build_vectorstore")
        assert fn is not None
        args = get_func_arg_names(fn)
        assert "documents" in args, \
            "build_vectorstore must accept 'documents' parameter"
        assert "persist_directory" in args, \
            "build_vectorstore must accept 'persist_directory' parameter"

    def test_uses_recursive_text_splitter(self):
        src = read_file("ingest.py")
        assert src is not None
        assert "RecursiveCharacterTextSplitter" in src, \
            "ingest.py must use RecursiveCharacterTextSplitter"

    def test_uses_huggingface_embeddings(self):
        src = read_file("ingest.py")
        assert src is not None
        assert "HuggingFaceEmbeddings" in src, \
            "ingest.py must use HuggingFaceEmbeddings"

    def test_uses_minilm_model(self):
        src = read_file("ingest.py")
        assert src is not None
        assert "all-MiniLM-L6-v2" in src, \
            "ingest.py must use sentence-transformers/all-MiniLM-L6-v2"

    def test_uses_chroma(self):
        src = read_file("ingest.py")
        assert src is not None
        assert "Chroma" in src, \
            "ingest.py must use ChromaDB (Chroma)"

    def test_main_block_exists(self):
        src = read_file("ingest.py")
        assert src is not None
        assert '__name__' in src and '__main__' in src, \
            "ingest.py must have a __main__ block"

    def test_main_prints_indexed_format(self):
        src = read_file("ingest.py")
        assert src is not None
        # Should contain the "Indexed" output format
        assert "Indexed" in src, \
            "ingest.py __main__ must print 'Indexed {N} chunks from {pdf_path}'"


# ============================================================================
# 4. rag_chain.py tests — structure and function signatures
# ============================================================================

class TestRagChainPy:
    """rag_chain.py must define get_retriever, build_rag_chain, query."""

    def test_syntax_valid(self):
        tree = parse_ast("rag_chain.py")
        assert tree is not None, "rag_chain.py has syntax errors or is missing"

    def test_get_retriever_exists(self):
        tree = parse_ast("rag_chain.py")
        assert tree is not None
        funcs = get_function_defs(tree)
        assert "get_retriever" in funcs, \
            "Function 'get_retriever' not found in rag_chain.py"

    def test_get_retriever_params(self):
        tree = parse_ast("rag_chain.py")
        assert tree is not None
        funcs = get_function_defs(tree)
        fn = funcs.get("get_retriever")
        assert fn is not None
        args = get_func_arg_names(fn)
        assert "persist_directory" in args, \
            "get_retriever must accept 'persist_directory' parameter"
        assert "k" in args, \
            "get_retriever must accept 'k' parameter"

    def test_build_rag_chain_exists(self):
        tree = parse_ast("rag_chain.py")
        assert tree is not None
        funcs = get_function_defs(tree)
        assert "build_rag_chain" in funcs, \
            "Function 'build_rag_chain' not found in rag_chain.py"

    def test_build_rag_chain_params(self):
        tree = parse_ast("rag_chain.py")
        assert tree is not None
        funcs = get_function_defs(tree)
        fn = funcs.get("build_rag_chain")
        assert fn is not None
        args = get_func_arg_names(fn)
        assert "retriever" in args, \
            "build_rag_chain must accept 'retriever' parameter"
        assert "model_name" in args, \
            "build_rag_chain must accept 'model_name' parameter"

    def test_query_exists(self):
        tree = parse_ast("rag_chain.py")
        assert tree is not None
        funcs = get_function_defs(tree)
        assert "query" in funcs, \
            "Function 'query' not found in rag_chain.py"

    def test_query_params(self):
        tree = parse_ast("rag_chain.py")
        assert tree is not None
        funcs = get_function_defs(tree)
        fn = funcs.get("query")
        assert fn is not None
        args = get_func_arg_names(fn)
        assert "chain" in args, \
            "query must accept 'chain' parameter"
        assert "question" in args, \
            "query must accept 'question' parameter"

    def test_uses_chat_ollama(self):
        src = read_file("rag_chain.py")
        assert src is not None
        assert "ChatOllama" in src, \
            "rag_chain.py must use ChatOllama from langchain_ollama"

    def test_uses_prompt_template(self):
        src = read_file("rag_chain.py")
        assert src is not None
        # Should use some form of prompt template
        has_prompt = ("ChatPromptTemplate" in src or
                      "PromptTemplate" in src or
                      "prompt" in src.lower())
        assert has_prompt, \
            "rag_chain.py must use a prompt template with context and question"

    def test_prompt_has_context_and_question(self):
        src = read_file("rag_chain.py")
        assert src is not None
        assert "{context}" in src or "context" in src, \
            "rag_chain.py prompt must include a {context} variable"
        assert "{question}" in src or "question" in src, \
            "rag_chain.py prompt must include a {question} variable"

    def test_uses_minilm_model(self):
        src = read_file("rag_chain.py")
        assert src is not None
        assert "all-MiniLM-L6-v2" in src, \
            "rag_chain.py must use all-MiniLM-L6-v2 embeddings"

    def test_query_returns_dict_structure(self):
        """Verify query function body references 'answer' and 'sources' keys."""
        src = read_file("rag_chain.py")
        assert src is not None
        assert '"answer"' in src or "'answer'" in src, \
            "query() must return a dict with 'answer' key"
        assert '"sources"' in src or "'sources'" in src, \
            "query() must return a dict with 'sources' key"


# ============================================================================
# 5. app.py tests — Flask application structure
# ============================================================================

class TestAppPy:
    """app.py must define a Flask app with correct routes."""

    def test_syntax_valid(self):
        tree = parse_ast("app.py")
        assert tree is not None, "app.py has syntax errors or is missing"

    def test_flask_app_named_app(self):
        src = read_file("app.py")
        assert src is not None
        # Must have `app = Flask(...)` assignment
        assert re.search(r'app\s*=\s*Flask\s*\(', src), \
            "app.py must define 'app = Flask(...)'"

    def test_ask_route_defined(self):
        src = read_file("app.py")
        assert src is not None
        assert "/ask" in src, \
            "app.py must define a '/ask' route"

    def test_ask_route_is_post(self):
        src = read_file("app.py")
        assert src is not None
        assert "POST" in src, \
            "The /ask route must accept POST method"

    def test_index_route_defined(self):
        src = read_file("app.py")
        assert src is not None
        # GET / route — either explicit or via @app.route("/")
        assert re.search(r'@app\.route\s*\(\s*["\']\/["\']\s*\)', src) or \
               re.search(r'@app\.route\s*\(\s*["\']\/["\']\s*,', src), \
            "app.py must define a GET '/' route"

    def test_renders_template(self):
        src = read_file("app.py")
        assert src is not None
        assert "render_template" in src, \
            "app.py must use render_template for the index route"
        assert "index.html" in src, \
            "app.py must render 'index.html'"

    def test_returns_json_response(self):
        src = read_file("app.py")
        assert src is not None
        assert "jsonify" in src, \
            "app.py must use jsonify for JSON responses"

    def test_error_handling_400(self):
        src = read_file("app.py")
        assert src is not None
        assert "400" in src, \
            "app.py must return HTTP 400 for missing/empty question"

    def test_error_message_for_missing_question(self):
        src = read_file("app.py")
        assert src is not None
        assert "error" in src.lower(), \
            "app.py must return an error message for invalid requests"

    def test_host_and_port(self):
        src = read_file("app.py")
        assert src is not None
        assert "5000" in src, \
            "app.py must serve on port 5000"
        assert "0.0.0.0" in src, \
            "app.py must bind to 0.0.0.0"


# ============================================================================
# 6. templates/index.html tests — Chat UI
# ============================================================================

class TestIndexHtml:
    """index.html must be a functional chat UI."""

    def test_is_valid_html(self):
        src = read_file("templates/index.html")
        assert src is not None, "templates/index.html missing"
        assert src.strip(), "templates/index.html is empty"
        src_lower = src.lower()
        assert "<html" in src_lower, "Must be a valid HTML document"
        assert "</html>" in src_lower, "Must have closing </html> tag"

    def test_has_input_field(self):
        src = read_file("templates/index.html")
        assert src is not None
        src_lower = src.lower()
        assert '<input' in src_lower or '<textarea' in src_lower, \
            "index.html must have an input field for questions"

    def test_has_send_button(self):
        src = read_file("templates/index.html")
        assert src is not None
        src_lower = src.lower()
        assert '<button' in src_lower, \
            "index.html must have a send/submit button"

    def test_uses_fetch_or_xhr(self):
        src = read_file("templates/index.html")
        assert src is not None
        assert "fetch" in src or "XMLHttpRequest" in src or "axios" in src, \
            "index.html must use fetch/XHR/axios to call the /ask endpoint"

    def test_calls_ask_endpoint(self):
        src = read_file("templates/index.html")
        assert src is not None
        assert "/ask" in src, \
            "index.html must send requests to the /ask endpoint"

    def test_sends_json_content_type(self):
        src = read_file("templates/index.html")
        assert src is not None
        assert "application/json" in src, \
            "index.html must send Content-Type: application/json"

    def test_has_css_styling(self):
        src = read_file("templates/index.html")
        assert src is not None
        src_lower = src.lower()
        assert "<style" in src_lower or 'rel="stylesheet"' in src_lower, \
            "index.html must include CSS styling"

    def test_has_javascript(self):
        src = read_file("templates/index.html")
        assert src is not None
        assert "<script" in src.lower(), \
            "index.html must include JavaScript"


# ============================================================================
# 7. docker-compose.yml tests
# ============================================================================

class TestDockerCompose:
    """docker-compose.yml must define ollama and app services."""

    def _load_compose(self):
        import yaml
        content = read_file("docker-compose.yml")
        assert content is not None, "docker-compose.yml missing"
        assert content.strip(), "docker-compose.yml is empty"
        data = yaml.safe_load(content)
        assert isinstance(data, dict), "docker-compose.yml must be valid YAML"
        return data

    def test_valid_yaml(self):
        self._load_compose()

    def test_has_services(self):
        data = self._load_compose()
        assert "services" in data, "docker-compose.yml must define 'services'"
        assert isinstance(data["services"], dict)

    def test_ollama_service(self):
        data = self._load_compose()
        services = data.get("services", {})
        assert "ollama" in services, \
            "docker-compose.yml must define an 'ollama' service"

    def test_ollama_image(self):
        data = self._load_compose()
        ollama = data["services"].get("ollama", {})
        image = ollama.get("image", "")
        assert "ollama" in image.lower(), \
            "ollama service must use an ollama image"


    def test_ollama_port(self):
        data = self._load_compose()
        ollama = data["services"].get("ollama", {})
        ports = str(ollama.get("ports", []))
        assert "11434" in ports, \
            "ollama service must expose port 11434"

    def test_app_service(self):
        data = self._load_compose()
        services = data.get("services", {})
        has_app = "app" in services or "web" in services
        assert has_app, \
            "docker-compose.yml must define an 'app' or 'web' service"

    def test_app_port(self):
        data = self._load_compose()
        services = data.get("services", {})
        app_svc = services.get("app", services.get("web", {}))
        ports = str(app_svc.get("ports", []))
        assert "5000" in ports, \
            "app service must expose port 5000"

    def test_app_depends_on_ollama(self):
        data = self._load_compose()
        services = data.get("services", {})
        app_svc = services.get("app", services.get("web", {}))
        depends = app_svc.get("depends_on", [])
        # depends_on can be a list or dict
        if isinstance(depends, dict):
            depends = list(depends.keys())
        assert "ollama" in depends, \
            "app service must depend on ollama service"

    def test_named_volume_exists(self):
        data = self._load_compose()
        volumes = data.get("volumes", {})
        assert volumes is not None and len(volumes) > 0, \
            "docker-compose.yml must define at least one named volume"


# ============================================================================
# 8. Dockerfile tests
# ============================================================================

class TestDockerfile:
    """Dockerfile must use Python base, install deps, expose 5000."""

    def _read_dockerfile(self):
        content = read_file("Dockerfile")
        assert content is not None, "Dockerfile missing"
        assert content.strip(), "Dockerfile is empty"
        return content

    def test_python_base_image(self):
        content = self._read_dockerfile()
        # FROM line should reference python
        from_lines = [l for l in content.splitlines()
                      if l.strip().upper().startswith("FROM")]
        assert len(from_lines) > 0, "Dockerfile must have a FROM instruction"
        assert any("python" in l.lower() for l in from_lines), \
            "Dockerfile must use a Python base image"

    def test_copies_requirements(self):
        content = self._read_dockerfile()
        assert "requirements" in content.lower(), \
            "Dockerfile must COPY requirements.txt"

    def test_installs_dependencies(self):
        content = self._read_dockerfile()
        assert "pip install" in content or "pip3 install" in content, \
            "Dockerfile must install Python dependencies via pip"

    def test_exposes_5000(self):
        content = self._read_dockerfile()
        expose_lines = [l for l in content.splitlines()
                        if l.strip().upper().startswith("EXPOSE")]
        assert any("5000" in l for l in expose_lines), \
            "Dockerfile must EXPOSE 5000"

    def test_has_cmd_or_entrypoint(self):
        content = self._read_dockerfile()
        upper = content.upper()
        assert "CMD" in upper or "ENTRYPOINT" in upper, \
            "Dockerfile must have a CMD or ENTRYPOINT to run the app"

    def test_copies_source(self):
        content = self._read_dockerfile()
        upper = content.upper()
        copy_count = upper.count("COPY")
        assert copy_count >= 2, \
            "Dockerfile must COPY both requirements.txt and application source"


# ============================================================================
# 9. README.md tests
# ============================================================================

class TestReadme:
    """README.md must include quick-start, curl example, ingestion steps."""

    def _read_readme(self):
        content = read_file("README.md")
        assert content is not None, "README.md missing"
        assert content.strip(), "README.md is empty"
        return content

    def test_not_trivially_short(self):
        content = self._read_readme()
        assert len(content.strip()) > 200, \
            "README.md is too short to contain required sections"

    def test_has_quick_start(self):
        content = self._read_readme()
        content_lower = content.lower()
        has_quickstart = ("quick start" in content_lower or
                          "quickstart" in content_lower or
                          "getting started" in content_lower or
                          "docker-compose up" in content_lower or
                          "docker compose up" in content_lower)
        assert has_quickstart, \
            "README.md must include a quick-start section"

    def test_has_docker_compose_instructions(self):
        content = self._read_readme()
        assert "docker-compose" in content.lower() or "docker compose" in content.lower(), \
            "README.md must include Docker Compose instructions"

    def test_has_curl_example(self):
        content = self._read_readme()
        assert "curl" in content.lower(), \
            "README.md must include a curl example for the /ask endpoint"

    def test_curl_references_ask_endpoint(self):
        content = self._read_readme()
        assert "/ask" in content, \
            "README.md curl example must reference the /ask endpoint"

    def test_has_ingestion_instructions(self):
        content = self._read_readme()
        content_lower = content.lower()
        has_ingest = ("ingest" in content_lower or
                      "index" in content_lower or
                      "pdf" in content_lower)
        assert has_ingest, \
            "README.md must include instructions for ingesting PDF documents"


# ============================================================================
# 10. Cross-file integration checks
# ============================================================================

class TestIntegration:
    """Cross-file consistency checks."""

    def test_app_imports_rag_chain(self):
        """app.py should import from rag_chain module."""
        src = read_file("app.py")
        assert src is not None
        assert "rag_chain" in src or "from rag_chain" in src or "import rag_chain" in src, \
            "app.py must import from rag_chain module"

    def test_rag_chain_imports_chroma(self):
        """rag_chain.py should use Chroma for retrieval."""
        src = read_file("rag_chain.py")
        assert src is not None
        assert "Chroma" in src, \
            "rag_chain.py must use Chroma vector store"

    def test_ingest_and_rag_chain_same_embedding(self):
        """Both ingest.py and rag_chain.py must use the same embedding model."""
        ingest_src = read_file("ingest.py")
        rag_src = read_file("rag_chain.py")
        assert ingest_src is not None and rag_src is not None
        assert "all-MiniLM-L6-v2" in ingest_src, \
            "ingest.py must use all-MiniLM-L6-v2"
        assert "all-MiniLM-L6-v2" in rag_src, \
            "rag_chain.py must use all-MiniLM-L6-v2"

    def test_default_model_is_llama(self):
        """rag_chain.py should default to a llama model."""
        src = read_file("rag_chain.py")
        assert src is not None
        assert "llama" in src.lower(), \
            "rag_chain.py should default to a llama model for Ollama"

    def test_docker_compose_app_has_build(self):
        """The app service in docker-compose should build from Dockerfile."""
        import yaml
        content = read_file("docker-compose.yml")
        assert content is not None
        data = yaml.safe_load(content)
        services = data.get("services", {})
        app_svc = services.get("app", services.get("web", {}))
        has_build = "build" in app_svc
        assert has_build, \
            "app service in docker-compose.yml must have a 'build' directive"

    def test_docker_compose_ollama_env_in_app(self):
        """The app service should pass OLLAMA_HOST env to connect to ollama."""
        import yaml
        content = read_file("docker-compose.yml")
        assert content is not None
        data = yaml.safe_load(content)
        services = data.get("services", {})
        app_svc = services.get("app", services.get("web", {}))
        env = app_svc.get("environment", [])
        env_str = str(env).lower()
        assert "ollama" in env_str, \
            "app service must set OLLAMA_HOST environment variable"

