"""
chunker.py — AST-based semantic code chunker.
Splits Python source into logical units (functions/classes) for focused LLM analysis.
Falls back to line-based chunking for non-Python files or unparseable code.
"""

import ast
from dataclasses import dataclass
from config import MAX_CHUNK_LINES


@dataclass
class CodeChunk:
    name: str
    chunk_type: str       # "function" | "class" | "module_level" | "raw_block"
    start_line: int
    end_line: int
    code: str
    language: str = "python"


def chunk_python(source_code: str) -> list[CodeChunk]:
    """Parse Python source with AST and extract top-level functions and classes."""
    chunks = []
    lines = source_code.splitlines()

    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        # Fallback: treat whole file as one raw block
        return [CodeChunk(
            name="<whole_file>",
            chunk_type="raw_block",
            start_line=1,
            end_line=len(lines),
            code=source_code,
        )]

    top_level_nodes = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            top_level_nodes.append(node)

    covered_lines = set()

    for node in top_level_nodes:
        start = node.lineno - 1
        end = node.end_lineno
        chunk_lines = lines[start:end]
        covered_lines.update(range(start, end))

        chunk_type = "class" if isinstance(node, ast.ClassDef) else "function"

        # If chunk is too large, sub-chunk by methods inside classes
        if len(chunk_lines) > MAX_CHUNK_LINES and isinstance(node, ast.ClassDef):
            sub_chunks = _sub_chunk_class(node, lines)
            chunks.extend(sub_chunks)
        else:
            chunks.append(CodeChunk(
                name=node.name,
                chunk_type=chunk_type,
                start_line=node.lineno,
                end_line=node.end_lineno,
                code="\n".join(chunk_lines),
            ))

    # Capture module-level code not inside any function/class
    module_lines = []
    module_start = None
    for i, line in enumerate(lines):
        if i not in covered_lines:
            if module_start is None:
                module_start = i
            module_lines.append(line)

    if module_lines:
        chunks.append(CodeChunk(
            name="<module_level>",
            chunk_type="module_level",
            start_line=(module_start or 0) + 1,
            end_line=(module_start or 0) + len(module_lines),
            code="\n".join(module_lines),
        ))

    return chunks


def _sub_chunk_class(class_node: ast.ClassDef, lines: list[str]) -> list[CodeChunk]:
    """Break large classes into method-level chunks."""
    chunks = []
    for node in ast.iter_child_nodes(class_node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno - 1
            end = node.end_lineno
            chunks.append(CodeChunk(
                name=f"{class_node.name}.{node.name}",
                chunk_type="function",
                start_line=node.lineno,
                end_line=node.end_lineno,
                code="\n".join(lines[start:end]),
            ))
    if not chunks:
        # No methods found, return the whole class
        start = class_node.lineno - 1
        end = class_node.end_lineno
        chunks.append(CodeChunk(
            name=class_node.name,
            chunk_type="class",
            start_line=class_node.lineno,
            end_line=class_node.end_lineno,
            code="\n".join(lines[start:end]),
        ))
    return chunks


def chunk_raw(source_code: str, language: str = "unknown") -> list[CodeChunk]:
    """Line-based chunking for non-Python files."""
    lines = source_code.splitlines()
    chunks = []
    block_size = MAX_CHUNK_LINES

    for i in range(0, len(lines), block_size):
        block = lines[i : i + block_size]
        chunks.append(CodeChunk(
            name=f"block_{i // block_size + 1}",
            chunk_type="raw_block",
            start_line=i + 1,
            end_line=i + len(block),
            code="\n".join(block),
            language=language,
        ))
    return chunks


def chunk_file(source_code: str, filename: str = "file.py") -> list[CodeChunk]:
    """Main entry point. Detects language and routes to appropriate chunker."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "py":
        return chunk_python(source_code)
    elif ext in ("js", "ts", "jsx", "tsx"):
        return chunk_raw(source_code, language="javascript")
    elif ext in ("java",):
        return chunk_raw(source_code, language="java")
    elif ext in ("go",):
        return chunk_raw(source_code, language="go")
    else:
        return chunk_raw(source_code, language=ext or "unknown")