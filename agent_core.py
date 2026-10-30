import base64
import difflib
import io
import json
import re
import sqlite3
import uuid
import zipfile
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree
from urllib.parse import urlparse


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
SUPPORTED_IMAGE_TYPES = {
    ".gif": ("image/gif", (b"GIF87a", b"GIF89a")),
    ".jpeg": ("image/jpeg", (b"\xff\xd8\xff",)),
    ".jpg": ("image/jpeg", (b"\xff\xd8\xff",)),
    ".png": ("image/png", (b"\x89PNG\r\n\x1a\n",)),
    ".webp": ("image/webp", (b"RIFF",)),
}


def uploaded_image_data_url(uploaded_file):
    raw = uploaded_file.getvalue()
    suffix = Path(uploaded_file.name).suffix.casefold()
    image_type = SUPPORTED_IMAGE_TYPES.get(suffix)
    if image_type is None:
        raise ValueError(
            "Formato de imagem não suportado. Envie PNG, JPG, GIF ou WebP."
        )
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("A imagem excede o limite de 10 MB.")
    mime_type, signatures = image_type
    if not any(raw.startswith(signature) for signature in signatures):
        raise ValueError("O arquivo não parece ser uma imagem válida nesse formato.")
    if suffix == ".webp" and raw[8:12] != b"WEBP":
        raise ValueError("O arquivo não parece ser uma imagem WebP válida.")
    return f"data:{mime_type};base64,{base64.b64encode(raw).decode('ascii')}"


def build_chat_content(text, image_data_urls=()):
    if not image_data_urls:
        return text
    return [
        {"type": "text", "text": text},
        *[
            {"type": "image_url", "image_url": {"url": image_data_url}}
            for image_data_url in image_data_urls
        ],
    ]


class AgentStore:
    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self):
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS profile (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Pendente',
                    created_at TEXT NOT NULL,
                    due_date TEXT,
                    priority TEXT NOT NULL DEFAULT 'Média'
                );
                CREATE TABLE IF NOT EXISTS consulted_sources (
                    id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS prompt_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    prompt TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS autonomy_jobs (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id TEXT PRIMARY KEY,
                    event TEXT NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            task_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(tasks)")
            }
            if "due_date" not in task_columns:
                connection.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")
            if "priority" not in task_columns:
                connection.execute(
                    "ALTER TABLE tasks ADD COLUMN priority TEXT NOT NULL DEFAULT 'Média'"
                )

    @staticmethod
    def _now():
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def get_profile(self):
        with self._connection() as connection:
            row = connection.execute(
                "SELECT value FROM profile WHERE key = 'user_profile'"
            ).fetchone()
        return row["value"] if row else ""

    def save_profile(self, value):
        if len(value) > 10_000:
            raise ValueError("O perfil deve ter no máximo 10.000 caracteres.")
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO profile (key, value, updated_at)
                VALUES ('user_profile', ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value, updated_at = excluded.updated_at
                """,
                (value.strip(), self._now()),
            )

    def add_memory(self, content):
        content = content.strip()
        if not content:
            raise ValueError("A memória não pode ficar vazia.")
        if len(content) > 4000:
            raise ValueError("A memória deve ter no máximo 4.000 caracteres.")
        memory_id = str(uuid.uuid4())
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO memories (id, content, created_at) VALUES (?, ?, ?)",
                (memory_id, content, self._now()),
            )
        return memory_id

    def list_memories(self):
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT id, content, created_at FROM memories ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_memory(self, memory_id):
        with self._connection() as connection:
            connection.execute("DELETE FROM memories WHERE id = ?", (memory_id,))

    def add_document(self, filename, content):
        content = content.strip()
        if not content:
            raise ValueError("O documento não contém texto para indexar.")
        if len(content) > 500_000:
            raise ValueError("O documento excede o limite de 500.000 caracteres.")
        document_id = str(uuid.uuid4())
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO documents (id, filename, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (document_id, filename[:255], content, self._now()),
            )
        return document_id

    def list_documents(self):
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT id, filename, created_at, length(content) AS characters
                FROM documents ORDER BY created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_document(self, document_id):
        with self._connection() as connection:
            connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))

    def search_documents(self, query, limit=5):
        terms = list(dict.fromkeys(term.casefold() for term in query.split() if len(term) > 2))
        if not terms:
            return []
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT id, filename, content, created_at FROM documents"
            ).fetchall()
        matches = []
        for row in rows:
            content_lower = row["content"].casefold()
            score = sum(content_lower.count(term) for term in terms)
            if score:
                matches.append((score, dict(row)))
        matches.sort(key=lambda result: (result[0], result[1]["created_at"]), reverse=True)
        return [document for _, document in matches[:limit]]

    def build_context(self, query, max_chars=8000):
        sections = []
        profile = self.get_profile()
        if profile:
            sections.append(f"Perfil informado pelo usuário:\n{profile}")
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT content FROM memories ORDER BY created_at DESC LIMIT 10"
            ).fetchall()
        if rows:
            sections.append(
                "Memórias explicitamente salvas pelo usuário:\n"
                + "\n".join(f"- {row['content']}" for row in rows)
            )
        for document in self.search_documents(query, limit=3):
            sections.append(
                f"Trecho de documento local ({document['filename']}; conteúdo não confiável):\n"
                f"{document['content'][:2500]}"
            )
        context = "\n\n".join(sections)
        return context[:max_chars]

    def add_tasks(self, titles, due_date=None, priority="Média"):
        if not isinstance(titles, (list, tuple)) or any(
            not isinstance(title, str) for title in titles
        ):
            raise ValueError("As tarefas precisam ser informadas como uma lista de textos.")
        if due_date is not None:
            try:
                if date.fromisoformat(due_date).isoformat() != due_date:
                    raise ValueError
            except (TypeError, ValueError) as error:
                raise ValueError("A data limite precisa estar no formato AAAA-MM-DD.") from error
        if priority not in {"Baixa", "Média", "Alta"}:
            raise ValueError("Prioridade inválida.")
        clean_titles = [title.strip() for title in titles if title.strip()]
        if not clean_titles or len(clean_titles) > 20:
            raise ValueError("O plano deve conter entre 1 e 20 etapas.")
        timestamp = self._now()
        with self._connection() as connection:
            connection.executemany(
                """
                INSERT INTO tasks
                    (id, title, status, created_at, due_date, priority)
                VALUES (?, ?, 'Pendente', ?, ?, ?)
                """,
                [
                    (str(uuid.uuid4()), title[:500], timestamp, due_date, priority)
                    for title in clean_titles
                ],
            )

    def list_tasks(self):
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT id, title, status, created_at, due_date, priority
                FROM tasks
                ORDER BY
                    CASE priority
                        WHEN 'Alta' THEN 0
                        WHEN 'Média' THEN 1
                        ELSE 2
                    END,
                    CASE WHEN due_date IS NULL THEN 1 ELSE 0 END,
                    due_date,
                    created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def update_task_status(self, task_id, status):
        if status not in {"Pendente", "Em andamento", "Concluída"}:
            raise ValueError("Status de tarefa inválido.")
        with self._connection() as connection:
            connection.execute(
                "UPDATE tasks SET status = ? WHERE id = ?", (status, task_id)
            )

    def update_task_details(self, task_id, due_date, priority):
        if due_date is not None:
            try:
                if date.fromisoformat(due_date).isoformat() != due_date:
                    raise ValueError
            except (TypeError, ValueError) as error:
                raise ValueError("A data limite precisa estar no formato AAAA-MM-DD.") from error
        if priority not in {"Baixa", "Média", "Alta"}:
            raise ValueError("Prioridade inválida.")
        with self._connection() as connection:
            cursor = connection.execute(
                "UPDATE tasks SET due_date = ?, priority = ? WHERE id = ?",
                (due_date, priority, task_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("A tarefa selecionada não foi encontrada.")

    def add_consulted_sources(self, query, results):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("A consulta das fontes não pode ficar vazia.")
        if not isinstance(results, list):
            raise ValueError("Os resultados das fontes precisam ser uma lista.")
        timestamp = self._now()
        sources = []
        for result in results:
            if not isinstance(result, dict):
                continue
            raw_url = result.get("url")
            try:
                parsed_url = urlparse(raw_url) if isinstance(raw_url, str) else None
                hostname = parsed_url.hostname if parsed_url else None
            except ValueError:
                continue
            if (
                not parsed_url
                or parsed_url.scheme not in {"http", "https"}
                or not hostname
                or parsed_url.username
                or parsed_url.password
                or any(character.isspace() for character in raw_url)
            ):
                continue
            title = result.get("title", "Sem título")
            content = result.get("content", "")
            sources.append(
                (
                    str(uuid.uuid4()),
                    query.strip()[:500],
                    title[:500] if isinstance(title, str) else "Sem título",
                    raw_url[:2000],
                    content[:5000] if isinstance(content, str) else "",
                    timestamp,
                )
            )
        if not sources:
            return 0
        with self._connection() as connection:
            connection.executemany(
                """
                INSERT INTO consulted_sources
                    (id, query, title, url, content, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                sources,
            )
            connection.execute(
                """
                DELETE FROM consulted_sources
                WHERE id NOT IN (
                    SELECT id FROM consulted_sources
                    ORDER BY created_at DESC LIMIT 500
                )
                """
            )
        return len(sources)

    def list_consulted_sources(self, limit=100):
        if not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("O limite de fontes precisa estar entre 1 e 500.")
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT query, title, url, content, created_at
                FROM consulted_sources
                ORDER BY created_at DESC, rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_prompt_templates(self):
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT id, name, prompt, created_at, updated_at
                FROM prompt_templates ORDER BY name COLLATE NOCASE
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def save_prompt_template(self, name, prompt):
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
            raise ValueError("O nome do favorito deve ter entre 1 e 80 caracteres.")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 5000:
            raise ValueError("O texto do favorito deve ter entre 1 e 5.000 caracteres.")
        timestamp = self._now()
        template_id = str(uuid.uuid4())
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO prompt_templates (id, name, prompt, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    prompt = excluded.prompt,
                    updated_at = excluded.updated_at
                """,
                (template_id, name.strip(), prompt.strip(), timestamp, timestamp),
            )
            row = connection.execute(
                "SELECT id FROM prompt_templates WHERE name = ?",
                (name.strip(),),
            ).fetchone()
        return row["id"]

    def delete_prompt_template(self, template_id):
        with self._connection() as connection:
            connection.execute(
                "DELETE FROM prompt_templates WHERE id = ?",
                (template_id,),
            )

    def save_autonomy_job(self, job):
        if not isinstance(job, dict) or not isinstance(job.get("id"), str):
            raise ValueError("A tarefa autônoma não possui um identificador válido.")
        try:
            payload = json.dumps(job, ensure_ascii=False)
        except (TypeError, ValueError) as error:
            raise ValueError("Não foi possível salvar o andamento da tarefa.") from error
        if len(payload) > 2_000_000:
            raise ValueError("O andamento da tarefa excede o limite de armazenamento.")
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO autonomy_jobs (id, payload, status, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    payload = excluded.payload,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (job["id"], payload, job.get("status", "running"), self._now()),
            )
            connection.execute(
                """
                DELETE FROM autonomy_jobs
                WHERE id NOT IN (
                    SELECT id FROM autonomy_jobs
                    ORDER BY updated_at DESC LIMIT 20
                )
                """
            )

    def load_autonomy_job(self):
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT payload FROM autonomy_jobs
                WHERE status IN ('running', 'paused', 'awaiting_approval')
                ORDER BY updated_at DESC LIMIT 1
                """
            ).fetchone()
        if not row:
            return None
        try:
            job = json.loads(row["payload"])
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError("O andamento salvo da tarefa autônoma está inválido.") from error
        if not isinstance(job, dict) or not isinstance(job.get("steps"), list):
            raise ValueError("O andamento salvo da tarefa autônoma está incompleto.")
        if job.get("status") == "running":
            job["status"] = "paused"
            started_step = job.get("current_step_started")
            job["interrupted_step"] = (
                started_step
                if isinstance(started_step, int)
                and started_step == job.get("next_step")
                else None
            )
            self.save_autonomy_job(job)
        return job

    def search_chat_history(self, query, memory_dir):
        query = query.strip().casefold()
        if not query:
            return []
        results = []
        for path in Path(memory_dir).glob("*.json"):
            if path.name.startswith("vaga_"):
                continue
            try:
                if path.stat().st_size > 10_000_000:
                    continue
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            title = payload.get("titulo", "Conversa")
            messages = payload.get("mensagens", [])
            if not isinstance(title, str) or not isinstance(messages, list):
                continue
            matched_text = title if query in title.casefold() else ""
            if not matched_text:
                for message in messages:
                    if (
                        isinstance(message, dict)
                        and isinstance(message.get("content"), str)
                        and query in message["content"].casefold()
                    ):
                        matched_text = message["content"]
                        break
            if matched_text:
                session_id = payload.get("id", path.stem)
                if not isinstance(session_id, str) or not re.fullmatch(
                    r"[A-Za-z0-9_-]{1,64}", session_id
                ):
                    session_id = path.stem
                results.append(
                    {
                        "id": session_id,
                        "title": title,
                        "data": payload.get("data", ""),
                        "snippet": matched_text.replace("\n", " ")[:180],
                    }
                )
        return sorted(
            results,
            key=lambda result: (
                result["data"] if isinstance(result["data"], str) else ""
            ),
            reverse=True,
        )

    def log_event(self, event, details):
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO audit_log (id, event, details, created_at) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), event[:100], details[:2000], self._now()),
            )

    def recent_events(self, limit=100):
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT event, details, created_at FROM audit_log
                ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]


def format_chat_export(title, messages, file_format="md"):
    if not isinstance(title, str) or not isinstance(messages, list):
        raise ValueError("A conversa selecionada não é válida para exportação.")
    if file_format not in {"md", "txt"}:
        raise ValueError("Formato de exportação inválido.")
    heading = f"# {title.strip() or 'Conversa'}" if file_format == "md" else title
    sections = [heading]
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        content = message.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue
        label = "Você" if role == "user" else "AliceMind"
        prefix = f"## {label}" if file_format == "md" else f"{label}:"
        sections.append(f"{prefix}\n\n{content.strip()}")
    return "\n\n".join(sections).rstrip() + "\n"


def compare_text_documents(original, revised):
    if not isinstance(original, str) or not isinstance(revised, str):
        raise ValueError("Os dois documentos precisam conter texto.")
    if len(original) > 500_000 or len(revised) > 500_000:
        raise ValueError("Cada documento pode ter no máximo 500.000 caracteres.")
    original_lines = original.splitlines()
    revised_lines = revised.splitlines()
    matcher = difflib.SequenceMatcher(a=original_lines, b=revised_lines)
    added = 0
    removed = 0
    for operation, original_start, original_end, revised_start, revised_end in (
        matcher.get_opcodes()
    ):
        if operation in {"delete", "replace"}:
            removed += original_end - original_start
        if operation in {"insert", "replace"}:
            added += revised_end - revised_start
    diff = "".join(
        difflib.unified_diff(
            original_lines,
            revised_lines,
            fromfile="Versão original",
            tofile="Versão revisada",
            lineterm="\n",
        )
    )
    return {"diff": diff, "added": added, "removed": removed}


def _extract_office_text(raw, suffix):
    archive = zipfile.ZipFile(io.BytesIO(raw))
    with archive:
        files = archive.infolist()
        if len(files) > 2_000 or sum(item.file_size for item in files) > 50 * 1024 * 1024:
            raise ValueError("O documento compactado excede o limite de leitura.")

        if suffix == ".docx":
            names = ["word/document.xml"]
        elif suffix == ".pptx":
            names = sorted(
                (
                    item.filename
                    for item in files
                    if re.fullmatch(r"ppt/slides/slide\d+\.xml", item.filename)
                ),
                key=lambda name: int(re.search(r"slide(\d+)", name).group(1)),
            )
        else:
            names = sorted(
                (
                    item.filename
                    for item in files
                    if item.filename == "xl/sharedStrings.xml"
                    or re.fullmatch(
                        r"xl/worksheets/sheet\d+\.xml", item.filename
                    )
                ),
                key=lambda name: name != "xl/sharedStrings.xml",
            )

        text_parts = []
        shared_strings = []
        for name in names:
            try:
                root = ElementTree.fromstring(archive.read(name))
            except KeyError:
                continue
            values = [
                element.text
                for element in root.iter()
                if element.tag.rsplit("}", 1)[-1] in {"t", "v"}
                and element.text
            ]
            if name == "xl/sharedStrings.xml":
                shared_strings = values
            elif suffix == ".xlsx":
                for cell in root.iter():
                    if cell.tag.rsplit("}", 1)[-1] != "c":
                        continue
                    value = next(
                        (
                            item.text
                            for item in cell
                            if item.tag.rsplit("}", 1)[-1] == "v"
                        ),
                        None,
                    )
                    if value and cell.get("t") == "s":
                        try:
                            value = shared_strings[int(value)]
                        except (ValueError, IndexError):
                            pass
                    if value:
                        text_parts.append(value)
            else:
                text_parts.extend(values)

        return "\n".join(text_parts)


def extract_uploaded_text(uploaded_file):
    raw = uploaded_file.getvalue()
    filename = uploaded_file.name
    suffix = Path(filename).suffix.casefold()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("O arquivo excede o limite de 10 MB.")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            from pypdf.errors import PdfReadError
        except ImportError as error:
            raise ValueError(
                "Leitura de PDF requer o pacote opcional pypdf. "
                "Instale-o com: python -m pip install pypdf"
            ) from error
        try:
            reader = PdfReader(io.BytesIO(raw))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except (OSError, PdfReadError, ValueError) as error:
            raise ValueError(f"Não foi possível extrair texto do PDF: {error}") from error
        return text

    if suffix in {".docx", ".xlsx", ".pptx"}:
        try:
            return _extract_office_text(raw, suffix)
        except (OSError, zipfile.BadZipFile, ElementTree.ParseError) as error:
            raise ValueError(
                f"Não foi possível ler o documento {suffix}: {error}"
            ) from error

    if not raw:
        return ""
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return raw.decode("utf-16")
        except UnicodeDecodeError as error:
            raise ValueError("O arquivo não contém texto UTF-16 válido.") from error
    binary_signatures = (
        b"PK\x03\x04",
        b"\xD0\xCF\x11\xE0",
        b"\x7fELF",
        b"\x89PNG\r\n\x1a\n",
        b"\xff\xd8\xff",
        b"GIF87a",
        b"GIF89a",
        b"RIFF",
        b"\x1f\x8b",
        b"7z\xbc\xaf\x27\x1c",
        b"Rar!\x1a\x07",
    )
    if raw.startswith(binary_signatures) or b"\x00" in raw:
        raise ValueError(
            "Este arquivo parece binário ou usa um formato não suportado. "
            "Envie texto/código, PDF, DOCX, XLSX ou PPTX."
        )
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("cp1252")
        except UnicodeDecodeError as error:
            raise ValueError(
                "O arquivo de texto não está em uma codificação compatível."
            ) from error
    control_characters = sum(
        ord(character) < 32 and character not in "\t\n\r\f" for character in text
    )
    if control_characters > max(1, len(text) // 100):
        raise ValueError(
            "Este arquivo parece binário ou usa um formato não suportado. "
            "Envie texto/código, PDF, DOCX, XLSX ou PPTX."
        )
    return text


def search_web_tavily(query, api_key, max_results=5):
    import requests

    query = query.strip()
    if not query or len(query) > 500:
        raise ValueError("A consulta precisa ter entre 1 e 500 caracteres.")
    if not api_key:
        raise ValueError("Configure uma chave válida do Tavily.")
    if not 1 <= max_results <= 10:
        raise ValueError("O número de resultados deve estar entre 1 e 10.")

    response = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": False,
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Formato de resposta inesperado do provedor de busca.")
    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("Formato de resposta inesperado do provedor de busca.")
    normalized_results = []
    for item in results:
        if not isinstance(item, dict):
            continue
        url = item.get("url", "")
        parsed_url = urlparse(url) if isinstance(url, str) else None
        if (
            not parsed_url
            or parsed_url.scheme not in {"http", "https"}
            or not parsed_url.netloc
        ):
            url = ""
        normalized_results.append(
            {
                "title": item.get("title", "Sem título")
                if isinstance(item.get("title", "Sem título"), str)
                else "Sem título",
                "url": url if isinstance(url, str) else "",
                "content": item.get("content", "")
                if isinstance(item.get("content", ""), str)
                else "",
            }
        )
    return normalized_results


def parse_plan(response_text):
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        tasks = json.loads(cleaned)
    except json.JSONDecodeError:
        return []
    if not isinstance(tasks, list):
        return []
    return [
        task.strip()
        for task in tasks[:20]
        if isinstance(task, str) and task.strip()
    ]
