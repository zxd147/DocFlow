from app.services.convert_file import (convert_pdf_to_docx, convert_docx_to_md_or_html, convert_pdf_to_md_or_html,
                                       convert_html_to_docx,
                                       convert_docx_to_pdf, convert_html_to_pdf, convert_excel_and_markdown_or_html,
                                       convert_html_to_html, convert_html_to_md, convert_md_to_html,
                                       convert_to_markdown)
from app.utils.logger import get_logger

logger = get_logger()

def get_file_conversion():
    conversion_map = {
        "pdf2docx": convert_pdf_to_docx,
        "docx2html": convert_docx_to_md_or_html,
        "pdf2html": convert_pdf_to_md_or_html,
        "html2docx": convert_html_to_docx,
        "docx2pdf": convert_docx_to_pdf,
        "html2pdf": convert_html_to_pdf,
    }
    markitdown_supported_types = {
        "pdf", "docx", "pptx", "xlsx", "xls", "csv", "html", "json",
        "xml", "txt", "epub", "zip", "jpg", "jpeg", "png", "mp3", "wav", "url"
    }
    for ext in markitdown_supported_types:
        conversion_map[f"{ext}2md"] = convert_to_markdown
    conversion_map["html2html"] = convert_html_to_html
    conversion_map["html2md"] = convert_html_to_md
    conversion_map["md2html"] = convert_md_to_html
    excel_related_map = {
        k: convert_excel_and_markdown_or_html for k in [
            "csv2xlsx", "csv2html", "csv2md",
            "xls2xlsx", "xls2html", "xls2md",
            "xlsx2csv", "xlsx2html", "xlsx2md",
            "html2xlsx", "html2csv", "md2xlsx",
        ]
    }
    conversion_map.update(excel_related_map)
    return conversion_map