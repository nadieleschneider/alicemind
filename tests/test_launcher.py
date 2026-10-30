import os
import sys
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from omni_launcher import make_control_server, run_streamlit_server


class LauncherControlTests(unittest.TestCase):
    def setUp(self):
        self.shutdown_requested = threading.Event()
        self.server = make_control_server(
            "test-token",
            self.shutdown_requested.set,
        )
        self.server_thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )
        self.server_thread.start()
        self.url = (
            f"http://127.0.0.1:{self.server.server_port}/shutdown"
        )

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=2)

    def test_shutdown_requires_local_secret_token(self):
        request = Request(self.url, data=b"", method="POST")

        with self.assertRaises(HTTPError) as error:
            urlopen(request, timeout=2)

        self.assertEqual(error.exception.code, 403)
        error.exception.close()
        self.assertFalse(self.shutdown_requested.is_set())

    def test_valid_shutdown_request_is_accepted(self):
        request = Request(
            self.url,
            data=b"",
            headers={"Authorization": "Bearer test-token"},
            method="POST",
        )

        with urlopen(request, timeout=2) as response:
            self.assertEqual(response.status, 202)

        self.assertTrue(self.shutdown_requested.wait(timeout=2))

    def test_unknown_control_path_is_rejected(self):
        request = Request(
            self.url + "/other",
            data=b"",
            headers={"Authorization": "Bearer test-token"},
            method="POST",
        )

        with self.assertRaises(HTTPError) as error:
            urlopen(request, timeout=2)

        self.assertEqual(error.exception.code, 404)
        error.exception.close()
        self.assertFalse(self.shutdown_requested.is_set())

    def test_streamlit_server_disables_development_mode_before_cli(self):
        original_environment = os.environ.get(
            "STREAMLIT_GLOBAL_DEVELOPMENT_MODE"
        )
        original_argv = sys.argv[:]

        def verify_production_mode():
            self.assertEqual(
                os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"],
                "false",
            )

        try:
            os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "true"
            with patch(
                "streamlit.web.cli.main",
                side_effect=verify_production_mode,
            ) as cli_main:
                run_streamlit_server(8765)

            cli_main.assert_called_once()
            self.assertIn("--server.port=8765", sys.argv)
        finally:
            sys.argv = original_argv
            if original_environment is None:
                os.environ.pop("STREAMLIT_GLOBAL_DEVELOPMENT_MODE", None)
            else:
                os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = (
                    original_environment
                )


if __name__ == "__main__":
    unittest.main()
