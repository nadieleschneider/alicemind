import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


AUTONOMOUS_ACTIONS = {
    "search_documents",
    "web_search",
    "create_tasks",
    "update_task",
    "draft_text",
    "write_file",
    "run_checks",
}

CHECKS = {"syntax", "unit_tests", "build_exe"}
EDITABLE_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}
PROTECTED_PARTS = {".git", ".omni_memory", "__pycache__", "build", "dist"}
PROTECTED_FILENAMES = {".env", "credentials.json", "secrets.json", "secrets.toml"}


def parse_autonomy_plan(response_text, max_steps=12):
    if not isinstance(response_text, str) or len(response_text) > 250_000:
        raise ValueError("A resposta do planejador está vazia ou excede o limite.")
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ValueError("O modelo não retornou um plano JSON válido.") from error

    if not isinstance(payload, dict) or set(payload) != {"steps"}:
        raise ValueError("O plano deve conter somente a lista 'steps'.")
    steps = payload["steps"]
    if not isinstance(steps, list) or not 1 <= len(steps) <= max_steps:
        raise ValueError(f"O plano deve conter entre 1 e {max_steps} etapas.")

    validated_steps = []
    for index, step in enumerate(steps, start=1):
        if (
            not isinstance(step, dict)
            or set(step) != {"action", "title", "params"}
            or not isinstance(step["action"], str)
            or step["action"] not in AUTONOMOUS_ACTIONS
            or not isinstance(step["title"], str)
            or not step["title"].strip()
            or len(step["title"]) > 200
            or not isinstance(step["params"], dict)
        ):
            raise ValueError(f"A etapa {index} tem formato ou ação inválida.")

        action = step["action"]
        params = step["params"]
        if action in {"search_documents", "web_search"}:
            _validate_exact_params(params, {"query"}, index)
            _validate_text(params["query"], 500, f"consulta da etapa {index}")
        elif action == "create_tasks":
            _validate_exact_params(params, {"titles"}, index)
            titles = params["titles"]
            if (
                not isinstance(titles, list)
                or not 1 <= len(titles) <= 10
                or any(
                    not isinstance(title, str)
                    or not title.strip()
                    or len(title) > 500
                    for title in titles
                )
            ):
                raise ValueError(f"A lista de tarefas da etapa {index} é inválida.")
        elif action == "update_task":
            _validate_exact_params(params, {"title", "status"}, index)
            _validate_text(params["title"], 500, f"título da etapa {index}")
            if not isinstance(params["status"], str) or params["status"] not in {
                "Pendente",
                "Em andamento",
                "Concluída",
            }:
                raise ValueError(f"O status da etapa {index} é inválido.")
        elif action == "draft_text":
            _validate_exact_params(params, {"prompt"}, index)
            _validate_text(params["prompt"], 5000, f"texto da etapa {index}")
        elif action == "write_file":
            _validate_exact_params(params, {"path", "content"}, index)
            _validate_text(params["path"], 500, f"caminho da etapa {index}")
            _validate_text(params["content"], 100_000, f"conteúdo da etapa {index}")
        elif action == "run_checks":
            _validate_exact_params(params, {"check"}, index)
            if not isinstance(params["check"], str) or params["check"] not in CHECKS:
                raise ValueError(f"A verificação da etapa {index} não é permitida.")

        validated_steps.append(
            {
                "action": action,
                "title": step["title"].strip(),
                "params": params,
            }
        )
    return validated_steps


def _validate_exact_params(params, required, index):
    if set(params) != required:
        raise ValueError(f"Os parâmetros da etapa {index} são inválidos.")


def _validate_text(value, max_length, label):
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError(f"O {label} precisa ter entre 1 e {max_length} caracteres.")


def resolve_project_file(project_root, relative_path):
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ValueError("Informe um caminho de arquivo dentro do projeto.")

    root = Path(project_root).resolve()
    requested = Path(relative_path)
    if (
        requested.is_absolute()
        or requested.drive
        or requested.anchor
        or any(part in {"..", "."} for part in requested.parts)
    ):
        raise ValueError("O caminho deve ser relativo e não pode sair do projeto.")
    if any(part.casefold() in PROTECTED_PARTS for part in requested.parts):
        raise ValueError("Esse caminho está protegido contra alterações.")
    if any(part.startswith(".") for part in requested.parts):
        raise ValueError("Arquivos ocultos ou de configuração não podem ser alterados.")
    if requested.name.casefold() in PROTECTED_FILENAMES:
        raise ValueError("Arquivos de credenciais não podem ser alterados.")
    if requested.suffix.casefold() not in EDITABLE_SUFFIXES:
        raise ValueError("A extensão desse arquivo não é permitida.")

    target = (root / requested).resolve()
    if not target.is_relative_to(root):
        raise ValueError("O caminho resolvido está fora do projeto.")
    return target


def write_project_file(
    project_root,
    relative_path,
    content,
    overwrite=False,
    expected_existing_hash=None,
):
    if not isinstance(content, str) or not content.strip():
        raise ValueError("O conteúdo do arquivo não pode ficar vazio.")
    if len(content) > 100_000:
        raise ValueError("O arquivo excede o limite de 100.000 caracteres.")

    target = resolve_project_file(project_root, relative_path)
    if target.exists() and not overwrite:
        raise FileExistsError(
            f"{relative_path} já existe e precisa de autorização para ser substituído."
        )
    if overwrite:
        if expected_existing_hash is None or not target.is_file():
            raise ValueError("A autorização para substituir esse arquivo não é válida.")
        current_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        if current_hash != expected_existing_hash:
            raise ValueError(
                "O arquivo mudou desde a autorização. Revise as novas alterações."
            )

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_file.write(content)
            temporary_path = Path(temporary_file.name)
        if overwrite:
            os.replace(temporary_path, target)
        else:
            os.link(temporary_path, target)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
    return target


def run_project_check(project_root, check_name, timeout=180):
    root = Path(project_root).resolve()
    if check_name not in CHECKS:
        raise ValueError("A verificação solicitada não está permitida.")

    if check_name == "syntax":
        excluded = PROTECTED_PARTS | {
            ".venv",
            "venv",
            "node_modules",
            ".pytest_cache",
        }
        files = []
        for current_dir, directories, filenames in os.walk(root):
            directories[:] = [
                name for name in directories if name.casefold() not in excluded
            ]
            files.extend(
                Path(current_dir) / filename
                for filename in filenames
                if filename.casefold().endswith(".py")
            )
            if len(files) > 500:
                raise ValueError("A verificação de sintaxe está limitada a 500 arquivos.")
        if not files:
            raise ValueError("Nenhum arquivo Python foi encontrado para verificar.")
        failures = []
        for path in files:
            try:
                if not path.resolve().is_relative_to(root):
                    raise ValueError("arquivo aponta para fora da pasta de projeto")
                if path.stat().st_size > 2 * 1024 * 1024:
                    raise ValueError("arquivo excede o limite de 2 MB")
                source = path.read_text(encoding="utf-8")
                compile(source, str(path), "exec")
            except (
                OSError,
                RuntimeError,
                SyntaxError,
                UnicodeError,
                ValueError,
            ) as error:
                failures.append(f"{path.relative_to(root)}: {error}")
        if failures:
            raise ValueError("Falhas de sintaxe:\n" + "\n".join(failures[:20]))
        return f"Sintaxe válida em {len(files)} arquivo(s) Python."

    if check_name == "unit_tests":
        if not (root / "tests").is_dir():
            raise ValueError("A pasta tests não existe na pasta de projeto autorizada.")
        environment = os.environ.copy()
        for name in (
            "OMNI_API_KEY",
            "TAVILY_API_KEY",
            "OMNI_SEARCH_API_KEY",
            "OMNI_DESKTOP_CONTROL_TOKEN",
        ):
            environment.pop(name, None)
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        output = (result.stdout + "\n" + result.stderr).strip()
        if result.returncode:
            raise ValueError(f"Os testes falharam (código {result.returncode}):\n{output[-12000:]}")
        return output[-12000:] or "Testes concluídos sem saída."

    if not (root / "omni.spec").is_file():
        raise ValueError(
            "O build do AliceMind exige omni.spec na pasta de projeto autorizada."
        )
    environment = os.environ.copy()
    for name in (
        "OMNI_API_KEY",
        "TAVILY_API_KEY",
        "OMNI_SEARCH_API_KEY",
        "OMNI_DESKTOP_CONTROL_TOKEN",
    ):
        environment.pop(name, None)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath",
            "dist",
            "--workpath",
            "build\\alicemind",
            "omni.spec",
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=max(timeout, 600),
        check=False,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode:
        raise ValueError(f"O build falhou (código {result.returncode}):\n{output[-12000:]}")
    return output[-12000:] or "Build concluído."
