import io

SUPPORTED_EXTENSIONS = {"pdf", "docx", "txt"}
MAX_CHARS = 8000


class UnsupportedFileType(ValueError):
    pass


def extract_text(filename: str, content: bytes) -> str:
    """Extract plain text from an uploaded PDF, DOCX, or TXT file.

    Only modern Word (.docx) is supported, not the legacy binary .doc
    format. Text is truncated to MAX_CHARS to keep the downstream OpenAI
    prompt a reasonable size.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileType(
            f"不支援的檔案格式:.{ext or '(無副檔名)'}。僅支援 PDF、Word(.docx)、TXT。"
        )

    if ext == "txt":
        text = content.decode("utf-8", errors="ignore")
    elif ext == "pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    else:  # docx
        from docx import Document

        doc = Document(io.BytesIO(content))
        text = "\n".join(p.text for p in doc.paragraphs)

    return text.strip()[:MAX_CHARS]
