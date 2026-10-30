import hashlib
import tempfile
import unittest
from pathlib import Path

from agent_executor import (
    parse_autonomy_plan,
    resolve_project_file,
    run_project_check,
    write_project_file,
)


class AutonomyPlanTests(unittest.TestCase):
    def test_parse_valid_plan(self):
        steps = parse_autonomy_plan(
            """```json
            {"steps": [
                {"action": "create_tasks", "title": "Salvar etapas",
                 "params": {"titles": ["Pesquisar dados", "Escrever resumo"]}},
                {"action": "run_checks", "title": "Validar sintaxe",
                 "params": {"check": "syntax"}}
            ]}
            ```"""
        )

        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]["action"], "create_tasks")
        self.assertEqual(steps[1]["params"]["check"], "syntax")

    def test_rejects_unknown_actions_and_unbounded_commands(self):
        invalid_plans = (
            '{"steps":[{"action":"send_email","title":"Enviar","params":{}}]}',
            '{"steps":[{"action":"run_checks","title":"Executar","params":{"check":"python -c anything"}}]}',
        )
        for plan in invalid_plans:
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                parse_autonomy_plan(plan)

    def test_rejects_missing_or_extra_parameters(self):
        with self.assertRaises(ValueError):
            parse_autonomy_plan(
                '{"steps":[{"action":"web_search","title":"Buscar","params":{"query":"x","url":"https://example.com"}}]}'
            )
        with self.assertRaises(ValueError):
            parse_autonomy_plan(
                '{"steps":[{"action":[],"title":"Inválida","params":{}}]}'
            )

    def test_rejects_more_than_twelve_steps(self):
        steps = [
            {"action": "search_documents", "title": "Busca", "params": {"query": "x"}}
            for _ in range(13)
        ]
        import json

        with self.assertRaises(ValueError):
            parse_autonomy_plan(json.dumps({"steps": steps}))


class SafeProjectFileTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_creates_project_file_and_requires_approval_to_overwrite(self):
        target = write_project_file(
            self.project_root,
            "notes/summary.md",
            "Draft one",
        )
        self.assertEqual(target.read_text(encoding="utf-8"), "Draft one")

        with self.assertRaises(FileExistsError):
            write_project_file(self.project_root, "notes/summary.md", "Draft two")

        original_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        write_project_file(
            self.project_root,
            "notes/summary.md",
            "Draft two",
            overwrite=True,
            expected_existing_hash=original_hash,
        )
        self.assertEqual(target.read_text(encoding="utf-8"), "Draft two")

    def test_refuses_overwrite_if_file_changed_after_approval(self):
        target = self.project_root / "notes.md"
        target.write_text("before", encoding="utf-8")
        approved_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        target.write_text("changed after review", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "mudou desde a autorização"):
            write_project_file(
                self.project_root,
                "notes.md",
                "replacement",
                overwrite=True,
                expected_existing_hash=approved_hash,
            )
        self.assertEqual(target.read_text(encoding="utf-8"), "changed after review")

    def test_rejects_paths_outside_or_into_protected_locations(self):
        for path in (
            "../outside.py",
            ".env",
            ".streamlit/secrets.toml",
            "dist/AliceMind.exe",
            "credentials.json",
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                resolve_project_file(self.project_root, path)

    def test_syntax_check_scans_project_python_without_running_it(self):
        (self.project_root / "app.py").write_text(
            "raise RuntimeError('must not execute')\n", encoding="utf-8"
        )

        result = run_project_check(self.project_root, "syntax")

        self.assertIn("Sintaxe válida", result)

    def test_syntax_check_reports_parse_errors(self):
        (self.project_root / "broken.py").write_text(
            "def incomplete(\n", encoding="utf-8"
        )

        with self.assertRaisesRegex(ValueError, "Falhas de sintaxe"):
            run_project_check(self.project_root, "syntax")

    def test_rejects_unlisted_checks(self):
        with self.assertRaises(ValueError):
            run_project_check(self.project_root, "powershell")


if __name__ == "__main__":
    unittest.main()
