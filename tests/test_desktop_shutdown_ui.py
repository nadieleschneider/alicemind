import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

from agent_core import AgentStore


class DesktopShutdownUITests(unittest.TestCase):
    def test_local_task_form_saves_deadline_and_priority(self):
        previous_memory_dir = os.environ.get("OMNI_MEMORY_DIR")
        with tempfile.TemporaryDirectory() as directory:
            memory_dir = Path(directory) / "memory"
            os.environ["OMNI_MEMORY_DIR"] = str(memory_dir)
            try:
                app = AppTest.from_file(
                    str(Path(__file__).resolve().parents[1] / "app.py"),
                    default_timeout=20,
                ).run()
                app.radio(key="workspace_navigation").set_value(
                    "Central do agente"
                ).run()
                next(
                    widget for widget in app.text_input if widget.label == "Nova tarefa"
                ).set_value("Preparar entrevista")
                next(
                    widget for widget in app.checkbox if widget.label == "Definir prazo"
                ).set_value(True).run()
                next(
                    widget for widget in app.date_input if widget.label == "Prazo"
                ).set_value(date(2026, 11, 5))
                next(
                    widget for widget in app.selectbox if widget.label == "Prioridade"
                ).set_value("Alta")
                next(
                    button
                    for button in app.button
                    if button.label == "Adicionar tarefa"
                ).click().run()

                self.assertFalse(app.exception, [e.message for e in app.exception])
                task = AgentStore(
                    memory_dir / "omni_agent.sqlite3"
                ).list_tasks()[0]
                self.assertEqual(task["title"], "Preparar entrevista")
                self.assertEqual(task["due_date"], "2026-11-05")
                self.assertEqual(task["priority"], "Alta")
            finally:
                if previous_memory_dir is None:
                    os.environ.pop("OMNI_MEMORY_DIR", None)
                else:
                    os.environ["OMNI_MEMORY_DIR"] = previous_memory_dir

    def test_autonomous_task_can_resume_from_local_checkpoint(self):
        names = ("OMNI_MEMORY_DIR", "OMNI_PROJECT_DIR")
        previous_values = {name: os.environ.get(name) for name in names}
        with tempfile.TemporaryDirectory() as directory:
            memory_dir = Path(directory) / "memory"
            project_root = Path(directory) / "workspace"
            project_root.mkdir()
            os.environ["OMNI_MEMORY_DIR"] = str(memory_dir)
            os.environ["OMNI_PROJECT_DIR"] = str(project_root)
            try:
                store = AgentStore(memory_dir / "omni_agent.sqlite3")
                store.save_autonomy_job(
                    {
                        "id": "resume-test",
                        "goal": "Retomar criação de tarefa",
                        "project_root": str(project_root),
                        "steps": [
                            {
                                "action": "create_tasks",
                                "title": "Criar tarefa local",
                                "params": {"titles": ["Revisar currículo"]},
                            }
                        ],
                        "next_step": 0,
                        "results": [],
                        "approved_steps": [],
                        "pending_approval": None,
                        "status": "running",
                        "current_step_started": 0,
                    }
                )
                app = AppTest.from_file(
                    str(Path(__file__).resolve().parents[1] / "app.py"),
                    default_timeout=20,
                ).run()
                app.radio(key="workspace_navigation").set_value(
                    "Central do agente"
                ).run()

                self.assertEqual(
                    app.session_state["autonomous_job"]["status"],
                    "paused",
                )
                self.assertFalse(store.list_tasks())
                next(
                    button
                    for button in app.button
                    if button.label == "Retomar tarefa salva"
                ).click().run()

                self.assertFalse(app.exception, [e.message for e in app.exception])
                self.assertEqual(
                    app.session_state["autonomous_job"]["status"],
                    "completed",
                )
                self.assertEqual(store.list_tasks()[0]["title"], "Revisar currículo")
            finally:
                for name, value in previous_values.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value

    def test_autonomous_plan_cannot_use_an_unselected_capability(self):
        previous_memory_dir = os.environ.get("OMNI_MEMORY_DIR")
        response = Mock()
        response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "steps": [
                                    {
                                        "action": "web_search",
                                        "title": "Pesquisar",
                                        "params": {"query": "consulta não autorizada"},
                                    }
                                ]
                            }
                        )
                    }
                }
            ]
        }
        response.raise_for_status.return_value = None

        with tempfile.TemporaryDirectory() as directory:
            memory_dir = Path(directory) / "memory"
            os.environ["OMNI_MEMORY_DIR"] = str(memory_dir)
            try:
                with patch("requests.post", return_value=response) as post:
                    app = AppTest.from_file(
                        str(Path(__file__).resolve().parents[1] / "app.py"),
                        default_timeout=20,
                    ).run()
                    app.radio(key="workspace_navigation").set_value(
                        "Central do agente"
                    ).run()
                    app.multiselect(key="autonomy_capabilities").set_value(
                        ["create_tasks"]
                    ).run()
                    app.text_area[1].set_value("Pesquise sem permitir buscas.")
                    next(
                        button
                        for button in app.button
                        if button.label == "Autorizar e executar pedido"
                    ).click().run()

                self.assertFalse(app.exception, [e.message for e in app.exception])
                self.assertEqual(post.call_count, 1)
                self.assertIsNone(app.session_state["autonomous_job"])
                self.assertTrue(app.error)
                self.assertFalse(
                    AgentStore(memory_dir / "omni_agent.sqlite3").list_tasks()
                )
            finally:
                if previous_memory_dir is None:
                    os.environ.pop("OMNI_MEMORY_DIR", None)
                else:
                    os.environ["OMNI_MEMORY_DIR"] = previous_memory_dir

    def test_autonomous_file_creation_stays_in_selected_workspace(self):
        names = ("OMNI_MEMORY_DIR", "OMNI_PROJECT_DIR")
        previous_values = {name: os.environ.get(name) for name in names}
        plan_response = Mock()
        plan_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "steps": [
                                    {
                                        "action": "write_file",
                                        "title": "Criar rascunho",
                                        "params": {
                                            "path": "notes/summary.md",
                                            "content": "# Rascunho\n\nConteúdo autorizado.",
                                        },
                                    }
                                ]
                            }
                        )
                    }
                }
            ]
        }
        plan_response.raise_for_status.return_value = None

        with tempfile.TemporaryDirectory() as directory:
            memory_dir = Path(directory) / "memory"
            project_root = Path(directory) / "workspace"
            project_root.mkdir()
            os.environ["OMNI_MEMORY_DIR"] = str(memory_dir)
            os.environ["OMNI_PROJECT_DIR"] = str(project_root)
            try:
                with patch("requests.post", return_value=plan_response):
                    app = AppTest.from_file(
                        str(Path(__file__).resolve().parents[1] / "app.py"),
                        default_timeout=20,
                    ).run()
                    app.radio(key="workspace_navigation").set_value(
                        "Central do agente"
                    ).run()
                    app.text_area[1].set_value("Crie um rascunho no projeto.")
                    next(
                        button
                        for button in app.button
                        if button.label == "Autorizar e executar pedido"
                    ).click().run()

                self.assertFalse(app.exception, [e.message for e in app.exception])
                self.assertEqual(
                    (project_root / "notes" / "summary.md").read_text(
                        encoding="utf-8"
                    ),
                    "# Rascunho\n\nConteúdo autorizado.",
                )
                self.assertEqual(
                    app.session_state["autonomous_job"]["status"],
                    "completed",
                )
            finally:
                for name, value in previous_values.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value

    def test_autonomous_web_search_waits_for_explicit_confirmation(self):
        names = ("OMNI_MEMORY_DIR", "TAVILY_API_KEY", "OMNI_SEARCH_API_KEY")
        previous_values = {name: os.environ.get(name) for name in names}
        plan_response = Mock()
        plan_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "steps": [
                                    {
                                        "action": "web_search",
                                        "title": "Pesquisar fontes",
                                        "params": {"query": "fontes sobre dados abertos"},
                                    }
                                ]
                            }
                        )
                    }
                }
            ]
        }
        plan_response.raise_for_status.return_value = None
        search_response = Mock()
        search_response.json.return_value = {
            "results": [
                {
                    "title": "Fonte confiável",
                    "url": "https://example.com/report",
                    "content": "Resumo da fonte.",
                }
            ]
        }
        search_response.raise_for_status.return_value = None

        with tempfile.TemporaryDirectory() as directory:
            os.environ["OMNI_MEMORY_DIR"] = str(Path(directory) / "memory")
            os.environ["TAVILY_API_KEY"] = "test-key"
            os.environ.pop("OMNI_SEARCH_API_KEY", None)
            try:
                with patch(
                    "requests.post",
                    side_effect=[plan_response, search_response],
                ) as post:
                    app = AppTest.from_file(
                        str(Path(__file__).resolve().parents[1] / "app.py"),
                        default_timeout=20,
                    ).run()
                    app.radio(key="workspace_navigation").set_value(
                        "Central do agente"
                    ).run()
                    app.text_area[1].set_value("Pesquise fontes sobre dados abertos.")
                    next(
                        button
                        for button in app.button
                        if button.label == "Autorizar e executar pedido"
                    ).click().run()

                    self.assertFalse(app.exception, [e.message for e in app.exception])
                    self.assertEqual(post.call_count, 1)
                    self.assertEqual(
                        app.session_state["autonomous_job"]["status"],
                        "awaiting_approval",
                    )

                    next(
                        checkbox
                        for checkbox in app.checkbox
                        if checkbox.label == "Entendo esta ação e autorizo sua execução."
                    ).check().run()
                    self.assertEqual(post.call_count, 1)

                    next(
                        button
                        for button in app.button
                        if button.label == "Autorizar esta ação e continuar"
                    ).click().run()

                self.assertFalse(app.exception, [e.message for e in app.exception])
                self.assertEqual(post.call_count, 2)
                self.assertEqual(
                    app.session_state["autonomous_job"]["status"],
                    "completed",
                )
                self.assertEqual(post.call_args_list[1].args[0], "https://api.tavily.com/search")
            finally:
                for name, value in previous_values.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value

    def test_autonomous_task_executes_only_its_authorized_local_action(self):
        previous_memory_dir = os.environ.get("OMNI_MEMORY_DIR")
        plan = {
            "steps": [
                {
                    "action": "create_tasks",
                    "title": "Salvar etapas",
                    "params": {"titles": ["Revisar requisitos", "Preparar rascunho"]},
                }
            ]
        }
        response = Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(plan)}}]
        }
        response.raise_for_status.return_value = None

        with tempfile.TemporaryDirectory() as directory:
            memory_dir = Path(directory) / "memory"
            os.environ["OMNI_MEMORY_DIR"] = str(memory_dir)
            try:
                with patch("requests.post", return_value=response) as post:
                    app = AppTest.from_file(
                        str(Path(__file__).resolve().parents[1] / "app.py"),
                        default_timeout=20,
                    ).run()
                    app.radio(key="workspace_navigation").set_value(
                        "Central do agente"
                    ).run()
                    app.text_area[1].set_value(
                        "Organize o trabalho em tarefas locais."
                    )
                    next(
                        button
                        for button in app.button
                        if button.label == "Autorizar e executar pedido"
                    ).click().run()

                self.assertFalse(app.exception, [e.message for e in app.exception])
                self.assertEqual(post.call_count, 1)
                tasks = AgentStore(memory_dir / "omni_agent.sqlite3").list_tasks()
                self.assertEqual(
                    {task["title"] for task in tasks},
                    {"Revisar requisitos", "Preparar rascunho"},
                )
                self.assertTrue(
                    any("Pedido concluído." in element.value for element in app.success)
                )
            finally:
                if previous_memory_dir is None:
                    os.environ.pop("OMNI_MEMORY_DIR", None)
                else:
                    os.environ["OMNI_MEMORY_DIR"] = previous_memory_dir

    def test_job_search_includes_all_requested_areas_and_roles(self):
        previous_memory_dir = os.environ.get("OMNI_MEMORY_DIR")

        with tempfile.TemporaryDirectory() as directory:
            os.environ["OMNI_MEMORY_DIR"] = str(Path(directory) / "memory")
            try:
                app = AppTest.from_file(
                    str(Path(__file__).resolve().parents[1] / "app.py"),
                    default_timeout=20,
                ).run()
                app.radio(key="workspace_navigation").set_value(
                    "Central global de vagas"
                ).run()

                self.assertFalse(app.exception, [e.message for e in app.exception])
                areas = next(
                    widget
                    for widget in app.multiselect
                    if widget.label == "Áreas profissionais para buscar"
                )
                self.assertEqual(len(areas.options), 6)
                self.assertEqual(list(areas.value), list(areas.options))

                conteudo_exibido = "\n".join(
                    elemento.value for elemento in app.markdown
                )
                for cargo in (
                    "Data Analyst",
                    "Python Developer",
                    "Clinical Data Analyst",
                    "LLM Evaluator",
                    "Technical Writer",
                    "Operations Analyst",
                ):
                    self.assertIn(cargo, conteudo_exibido)
            finally:
                if previous_memory_dir is None:
                    os.environ.pop("OMNI_MEMORY_DIR", None)
                else:
                    os.environ["OMNI_MEMORY_DIR"] = previous_memory_dir

    def test_sidebar_shutdown_opens_confirmation_dialog(self):
        previous_values = {
            name: os.environ.get(name)
            for name in (
                "OMNI_MEMORY_DIR",
                "OMNI_DESKTOP_CONTROL_URL",
                "OMNI_DESKTOP_CONTROL_TOKEN",
            )
        }

        with tempfile.TemporaryDirectory() as directory:
            os.environ["OMNI_MEMORY_DIR"] = str(Path(directory) / "memory")
            os.environ["OMNI_DESKTOP_CONTROL_URL"] = "http://127.0.0.1/shutdown"
            os.environ["OMNI_DESKTOP_CONTROL_TOKEN"] = "ui-test-token"
            try:
                app = AppTest.from_file(
                    str(Path(__file__).resolve().parents[1] / "app.py"),
                    default_timeout=20,
                ).run()
                self.assertFalse(app.exception, [e.message for e in app.exception])
                next(
                    button
                    for button in app.sidebar.button
                    if button.label == "Encerrar AliceMind"
                ).click().run()
                checkbox = next(
                    checkbox
                    for checkbox in app.checkbox
                    if checkbox.label == "Sim, quero encerrar o AliceMind."
                )
                shutdown_button = next(
                    button
                    for button in app.button
                    if button.label == "Encerrar programa"
                )
                self.assertFalse(checkbox.value)
                self.assertTrue(shutdown_button.disabled)
                self.assertFalse(app.exception, [e.message for e in app.exception])
            finally:
                for name, value in previous_values.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value


if __name__ == "__main__":
    unittest.main()
