import io
import unittest

from pypdf import PdfReader

from resume_pdf import create_resume_pdf


class ResumePdfTests(unittest.TestCase):
    def test_creates_a_readable_portuguese_pdf_with_resume_sections(self):
        pdf_bytes = create_resume_pdf(
            "# Perfil profissional\n"
            "Analista de dados em formação\n\n"
            "## FORMAÇÃO\n"
            "- Estudante de ADS\n\n"
            "## IDIOMAS\n"
            "- Inglês intermediário"
        )

        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        self.assertIn("Perfil profissional", text)
        self.assertIn("FORMAÇÃO", text)
        self.assertIn("Estudante de ADS", text)
        self.assertIn("Inglês intermediário", text)

    def test_rejects_empty_or_oversized_resume_text(self):
        with self.assertRaises(ValueError):
            create_resume_pdf(" ")
        with self.assertRaises(ValueError):
            create_resume_pdf("x" * 50_001)


if __name__ == "__main__":
    unittest.main()
