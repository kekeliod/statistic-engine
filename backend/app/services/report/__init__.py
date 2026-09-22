"""Structured research-report assembly and rendering (HTML, DOCX)."""

from app.services.report.builder import build_report_doc
from app.services.report.render_docx import render_docx
from app.services.report.render_html import render_html

__all__ = ["build_report_doc", "render_html", "render_docx"]
