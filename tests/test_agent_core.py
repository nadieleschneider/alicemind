import base64
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

from agent_core import (
    AgentStore,
    build_chat_content,
    compare_text_documents,
    extract_uploaded_text,
    format_chat_export,
    parse_plan,
    search_web_tavily,
    uploaded_image_data_url,
)


class UploadedTextTests(unittest.TestCase):
    def upload(self, name, content):
        return SimpleNamespace(name=name, getvalue=lambda: content)

    def test_extracts_source_code_and_sql_without_extension_allowlist(self):
        self.assertEqual(
            extract_uploaded_text(
                self.upload("main.py", b"print('hello')\n")
            ),
            "print('hello')\n",
        )
        self.assertEqual(
            extract_uploaded_text(
                self.upload("schema.sql", b"SELECT * FROM students;\n")
            ),
            "SELECT * FROM students;\n",
        )
        self.assertEqual(
            extract_uploaded_text(self.upload("server.conf", b"port=8080")),
            "port=8080",
        )

    def test_extracts_utf16_text_and_spreadsheet_cells(self):
        self.assertEqual(
            extract_uploaded_text(self.upload("anotacoes.txt", "UTF-16".encode("utf-16"))),
            "UTF-16",
        )
        content = io.BytesIO()
        with zipfile.ZipFile(content, "w") as archive:
            archive.writestr(
                "xl/sharedStrings.xml",
                '<sst xmlns="urn:spreadsheet"><si><t>Nome</t></si>'
                "<si><t>Ana</t></si></sst>",
            )
            archive.writestr(
                "xl/worksheets/sheet1.xml",
                '<worksheet xmlns="urn:spreadsheet"><row>'
                '<c r="A1" t="s"><v>0</v></c>'
                '<c r="A2" t="s"><v>1</v></c>'
                "</row></worksheet>",
            )

        self.assertEqual(
            extract_uploaded_text(self.upload("dados.xlsx", content.getvalue())),
            "Nome\nAna",
        )

    def test_extracts_text_from_word_document(self):
        content = io.BytesIO()
        with zipfile.ZipFile(content, "w") as archive:
            archive.writestr(
                "word/document.xml",
                '<document xmlns:w="urn:word"><w:p><w:r><w:t>Projeto '
                "Python</w:t></w:r></w:p></document>",
            )

        self.assertEqual(
            extract_uploaded_text(self.upload("relatorio.docx", content.getvalue())),
            "Projeto Python",
        )

    def test_rejects_binary_files_with_a_helpful_message(self):
        with self.assertRaisesRegex(ValueError, "binário"):
            extract_uploaded_text(self.upload("programa.exe", b"\x00\x01\x02"))

    def test_builds_multimodal_message_with_uploaded_png(self):
        image_bytes = b"\x89PNG\r\n\x1a\nimage"
        data_url = uploaded_image_data_url(self.upload("tela.png", image_bytes))

        self.assertTrue(data_url.startswith("data:image/png;base64,"))
        encoded_image = data_url.partition(",")[2]
        self.assertEqual(base64.b64decode(encoded_image), image_bytes)
        self.assertEqual(
            build_chat_content("Descreva esta tela.", [data_url]),
            [
                {"type": "text", "text": "Descreva esta tela."},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        )

    def test_rejects_invalid_image_extension_and_contents(self):
        with self.assertRaisesRegex(ValueError, "PNG, JPG, GIF ou WebP"):
            uploaded_image_data_url(self.upload("foto.bmp", b"BM image"))
        with self.assertRaisesRegex(ValueError, "imagem válida"):
            uploaded_image_data_url(self.upload("foto.png", b"not an image"))


class AgentStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = AgentStore(Path(self.temp_dir.name) / "agent.sqlite3")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_profile_memories_and_document_context_persist(self):
        self.store.save_profile("Respostas objetivas")
        self.store.add_memory("Prefere exemplos práticos")
        self.store.add_document("notas.txt", "Projeto de análise usando Python e SQL.")

        context = self.store.build_context("Python", max_chars=5000)

        self.assertIn("Respostas objetivas", context)
        self.assertIn("Prefere exemplos práticos", context)
        self.assertIn("notas.txt", context)
        self.assertEqual(len(self.store.search_documents("Python")), 1)

    def test_task_status_is_validated_and_persisted(self):
        self.store.add_tasks(["Pesquisar requisitos", "Criar protótipo"])
        task = self.store.list_tasks()[0]

        self.store.update_task_status(task["id"], "Em andamento")

        self.assertEqual(self.store.list_tasks()[0]["status"], "Em andamento")
        with self.assertRaises(ValueError):
            self.store.update_task_status(task["id"], "Executar automaticamente")

    def test_tasks_keep_optional_deadlines_and_priorities(self):
        self.store.add_tasks(
            ["Entregar relatório"],
            due_date="2026-11-05",
            priority="Alta",
        )
        task = self.store.list_tasks()[0]

        self.assertEqual(task["due_date"], "2026-11-05")
        self.assertEqual(task["priority"], "Alta")
        self.store.update_task_details(task["id"], None, "Baixa")
        updated = self.store.list_tasks()[0]
        self.assertIsNone(updated["due_date"])
        self.assertEqual(updated["priority"], "Baixa")
        with self.assertRaises(ValueError):
            self.store.add_tasks(["Inválida"], due_date="05/11/2026")

    def test_consulted_sources_keep_only_safe_http_links(self):
        count = self.store.add_consulted_sources(
            "pesquisa segura",
            [
                {
                    "title": "Fonte válida",
                    "url": "https://example.com/artigo",
                    "content": "Resumo",
                },
                {"title": "Link inseguro", "url": "javascript:alert(1)"},
            ],
        )

        self.assertEqual(count, 1)
        sources = self.store.list_consulted_sources()
        self.assertEqual(sources[0]["query"], "pesquisa segura")
        self.assertEqual(sources[0]["url"], "https://example.com/artigo")

    def test_prompt_favorites_can_be_saved_updated_and_deleted(self):
        template_id = self.store.save_prompt_template(
            "Revisão natural",
            "Revise este texto.",
        )
        self.store.save_prompt_template(
            "revisão natural",
            "Revise sem alterar meu tom.",
        )

        templates = self.store.list_prompt_templates()
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0]["id"], template_id)
        self.assertEqual(templates[0]["prompt"], "Revise sem alterar meu tom.")
        self.store.delete_prompt_template(template_id)
        self.assertFalse(self.store.list_prompt_templates())
        with self.assertRaises(ValueError):
            self.store.save_prompt_template("   ", "Texto")

    def test_autonomous_job_checkpoints_resume_as_paused_after_restart(self):
        job = {
            "id": "job-1",
            "status": "running",
            "next_step": 1,
            "steps": [{"title": "Uma etapa"}, {"title": "Próxima etapa"}],
            "current_step_started": 1,
        }
        self.store.save_autonomy_job(job)

        restored = self.store.load_autonomy_job()

        self.assertEqual(restored["status"], "paused")
        self.assertEqual(restored["interrupted_step"], 1)
        self.assertEqual(restored["next_step"], 1)
        self.assertEqual(self.store.load_autonomy_job()["status"], "paused")

    def test_existing_task_database_is_migrated_without_losing_tasks(self):
        legacy_path = Path(self.temp_dir.name) / "legacy.sqlite3"
        connection = sqlite3.connect(legacy_path)
        try:
            connection.execute(
                """
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Pendente',
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "INSERT INTO tasks (id, title, created_at) VALUES (?, ?, ?)",
                ("existing", "Tarefa existente", "2026-10-29T10:00:00"),
            )
            connection.commit()
        finally:
            connection.close()

        migrated = AgentStore(legacy_path).list_tasks()[0]

        self.assertEqual(migrated["title"], "Tarefa existente")
        self.assertIsNone(migrated["due_date"])
        self.assertEqual(migrated["priority"], "Média")

    def test_chat_history_search_and_exports(self):
        memory_dir = Path(self.temp_dir.name)
        (memory_dir / "chat-1.json").write_text(
            '{"id":"chat-1","titulo":"Projeto","data":"2026-10-29",'
            '"mensagens":[{"role":"user","content":"revisar proposta"}]}',
            encoding="utf-8",
        )
        results = self.store.search_chat_history("proposta", memory_dir)

        self.assertEqual(results[0]["title"], "Projeto")
        self.assertIn("proposta", results[0]["snippet"])
        markdown = format_chat_export(
            "Projeto",
            [
                {"role": "user", "content": "Olá"},
                {"role": "assistant", "content": "Bom dia"},
            ],
        )
        self.assertIn("## Você\n\nOlá", markdown)
        self.assertIn("## AliceMind\n\nBom dia", markdown)
        self.assertIn("Você:\n\nOlá", format_chat_export("Projeto", [
            {"role": "user", "content": "Olá"}
        ], "txt"))

    def test_document_comparison_counts_changed_lines(self):
        result = compare_text_documents(
            "linha mantida\nlinha antiga",
            "linha mantida\nlinha nova\nlinha extra",
        )

        self.assertEqual(result["added"], 2)
        self.assertEqual(result["removed"], 1)
        self.assertIn("-linha antiga", result["diff"])
        self.assertIn("+linha nova", result["diff"])

    def test_memory_and_document_limits_are_enforced(self):
        with self.assertRaises(ValueError):
            self.store.add_memory("x" * 4001)
        with self.assertRaises(ValueError):
            self.store.add_document("empty.txt", "  ")

    def test_parse_plan_accepts_json_and_rejects_other_shapes(self):
        self.assertEqual(
            parse_plan('```json\n["Uma etapa", "Outra etapa"]\n```'),
            ["Uma etapa", "Outra etapa"],
        )
        self.assertEqual(parse_plan('{"step": "not a list"}'), [])
        self.assertEqual(parse_plan("not json"), [])


class WebSearchTests(unittest.TestCase):
    @patch("requests.post")
    def test_search_returns_cited_results(self, post):
        response = Mock()
        response.json.return_value = {
            "results": [
                {"title": "Fonte", "url": "https://example.com", "content": "Resumo"},
                {"title": "Insegura", "url": "javascript:alert(1)", "content": "Texto"},
            ]
        }
        response.raise_for_status.return_value = None
        post.return_value = response

        results = search_web_tavily("consulta", "test-key")

        self.assertEqual(results[0]["url"], "https://example.com")
        self.assertEqual(results[1]["url"], "")
        post.assert_called_once()

    def test_search_rejects_empty_queries(self):
        with self.assertRaises(ValueError):
            search_web_tavily(" ", "test-key")

    @patch("requests.post")
    def test_search_propagates_provider_failures(self, post):
        post.side_effect = requests.Timeout("timeout")

        with self.assertRaises(requests.Timeout):
            search_web_tavily("consulta", "test-key")


if __name__ == "__main__":
    unittest.main()
