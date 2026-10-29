import os
import re
from pypdf import PdfReader
from docx import Document

class DocumentExtractor:
    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()

    @classmethod
    def extract_from_pdf(cls, file_path: str) -> str:
        text_parts = []
        reader = PdfReader(file_path)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text_parts.append(extracted)
        return cls.clean_text("\n".join(text_parts))

    @classmethod
    def extract_from_docx(cls, file_path: str) -> str:
        doc = Document(file_path)
        text_parts = [para.text for para in doc.paragraphs if para.text.strip()]
        return cls.clean_text("\n".join(text_parts))

    @classmethod
    def extract_from_txt(cls, file_path: str) -> str:
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return cls.clean_text(f.read())
            except UnicodeDecodeError:
                continue
        raise ValueError("Unable to decode text file with standard encodings.")

    @classmethod
    def extract(cls, file_path: str, extension: str) -> str:
        ext = extension.lower()
        if ext == ".pdf":
            return cls.extract_from_pdf(file_path)
        elif ext == ".docx":
            return cls.extract_from_docx(file_path)
        elif ext == ".txt":
            return cls.extract_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
