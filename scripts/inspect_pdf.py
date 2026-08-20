"""Return minimal, location-safe structural evidence for a generated PDF."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


class PdfDependencyError(RuntimeError):
    """Raised when the dev-only PyMuPDF inspector is unavailable."""


def _fitz_module() -> Any:
    try:
        import fitz
    except ModuleNotFoundError as error:
        raise PdfDependencyError("PyMuPDF is unavailable") from error
    return fitz


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError("arguments: invalid command")


def _link_target(link: dict[object, object]) -> str:
    uri = link.get("uri")
    if isinstance(uri, str):
        return uri
    page = link.get("page")
    if isinstance(page, int):
        return f"page:{page + 1}"
    name = link.get("name")
    return name if isinstance(name, str) else ""


def _normalized_page_text(page: Any) -> str:
    return " ".join(page.get_text("text").split())


def _rounded_box(value: Any) -> list[float]:
    return [round(float(channel), 2) for channel in value]


def _page_layout(page: Any) -> tuple[list[dict[str, object]], list[float], list[str]]:
    layout: list[dict[str, object]] = []
    sizes: set[float] = set()
    colors: set[str] = set()
    value = page.get_text("dict")
    for block in value.get("blocks", []) if isinstance(value, dict) else []:
        if not isinstance(block, dict) or block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []) if isinstance(line, dict) else []:
                if not isinstance(span, dict):
                    continue
                size = round(float(span.get("size", 0)), 2)
                color = f"#{int(span.get('color', 0)):06X}"
                sizes.add(size)
                colors.add(color)
                layout.append(
                    {
                        "bbox": _rounded_box(span.get("bbox", (0, 0, 0, 0))),
                        "font": str(span.get("font", "")),
                        "size": size,
                        "color": color,
                        "text_sha256": hashlib.sha256(" ".join(str(span.get("text", "")).split()).encode("utf-8")).hexdigest(),
                    }
                )
    return layout, sorted(sizes), sorted(colors)


def _embedded_files(document: Any) -> tuple[list[str], list[tuple[str, bytes]]]:
    try:
        names = sorted(str(name) for name in document.embfile_names())
    except (AttributeError, RuntimeError):
        return [], []
    files: list[tuple[str, bytes]] = []
    for name in names:
        try:
            content = document.embfile_get(name)
        except (KeyError, RuntimeError, ValueError):
            content = b""
        files.append((name, bytes(content)))
    return names, files


def _open_pdf(input_path: Path) -> Any:
    fitz = _fitz_module()
    try:
        return fitz.open(input_path)
    except (OSError, RuntimeError, ValueError):
        raise ValueError("pdf: could not inspect") from None


def inspect_pdf(input_path: Path) -> dict[str, object]:
    document = _open_pdf(input_path)
    try:
        pages = list(document)
        page_text = [_normalized_page_text(page) for page in pages]
        page_text_characters = [len(text) for text in page_text]
        page_text_sha256 = [hashlib.sha256(text.encode("utf-8")).hexdigest() for text in page_text]
        page_text_inventory_sha256 = [
            hashlib.sha256("\n".join(sorted(re.findall(r"\w+", text, flags=re.UNICODE))).encode("utf-8")).hexdigest()
            for text in page_text
        ]
        layouts = [_page_layout(page) for page in pages]
        page_layout_sha256 = [
            hashlib.sha256(json.dumps(layout, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
            for layout, _, _ in layouts
        ]
        page_dimensions = [[round(float(page.rect.width), 2), round(float(page.rect.height), 2)] for page in pages]
        page_text_block_count = [len(layout) for layout, _, _ in layouts]
        page_font_sizes = [sizes for _, sizes, _ in layouts]
        page_text_colors = [colors for _, _, colors in layouts]
        page_image_count = [len(page.get_images(full=True)) for page in pages]
        link_annotations = [
            {"page": page_number + 1, "target": _link_target(link)}
            for page_number, page in enumerate(pages)
            for link in page.get_links()
        ]
        attachment_names, _ = _embedded_files(document)
        metadata = {
            str(key): str(value)
            for key, value in sorted((document.metadata or {}).items())
            if value not in (None, "")
        }
    except (RuntimeError, ValueError):
        raise ValueError("pdf: could not inspect") from None
    finally:
        document.close()
    return {
        "page_count": len(page_text_characters),
        "page_text_characters": page_text_characters,
        "page_text_sha256": page_text_sha256,
        "page_text_inventory_sha256": page_text_inventory_sha256,
        "page_layout_sha256": page_layout_sha256,
        "page_dimensions": page_dimensions,
        "page_text_block_count": page_text_block_count,
        "page_font_sizes": page_font_sizes,
        "page_text_colors": page_text_colors,
        "page_image_count": page_image_count,
        "image_count": sum(page_image_count),
        "link_annotations": link_annotations,
        "metadata": metadata,
        "attachment_names": attachment_names,
    }


def validate_pdf_privacy(input_path: Path, location: str) -> list[str]:
    """Return location-safe privacy errors for text extracted from a public PDF."""
    from scripts.report_model import privacy_errors

    document = _open_pdf(input_path)
    try:
        errors: list[str] = []
        for page_number, page in enumerate(document, start=1):
            errors.extend(privacy_errors(_normalized_page_text(page), f"{location}.page[{page_number}]"))
            for link_index, link in enumerate(page.get_links()):
                errors.extend(privacy_errors(_link_target(link), f"{location}.page[{page_number}].link[{link_index}]"))
            if page.get_images(full=True):
                errors.append(f"{location}.page[{page_number}]: PDF images are not registered for inspection")
        errors.extend(privacy_errors(document.metadata or {}, f"{location}.metadata"))
        _, embedded_files = _embedded_files(document)
        for index, (name, content) in enumerate(embedded_files):
            errors.extend(privacy_errors(name, f"{location}.attachment[{index}].name"))
            errors.extend(privacy_errors(content.decode("utf-8", errors="replace"), f"{location}.attachment[{index}].content"))
        return errors
    except (RuntimeError, ValueError):
        raise ValueError("pdf: could not inspect") from None
    finally:
        document.close()


def main(argv: list[str] | None = None) -> int:
    parser = _SafeArgumentParser(add_help=False)
    parser.add_argument("--input", required=True, type=Path)
    try:
        arguments = parser.parse_args(argv)
    except ValueError:
        print("arguments: invalid command", file=sys.stderr)
        return 1
    if arguments.input.suffix.lower() != ".pdf":
        print("pdf: could not inspect", file=sys.stderr)
        return 1
    try:
        evidence = inspect_pdf(arguments.input)
    except (PdfDependencyError, ValueError):
        print("pdf: could not inspect", file=sys.stderr)
        return 1
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
