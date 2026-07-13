from __future__ import annotations

import json
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .log import Logger, emit
from .paths import materialize_tool_dir, resource_path


ARCHIVE_EXTENSIONS = {
    ".zip",
    ".rar",
    ".7z",
    ".cbz",
    ".cbr",
    ".cb7",
    ".epub",
    ".tar",
    ".gz",
    ".tgz",
    ".tar.gz",
    ".bz2",
    ".tar.bz2",
    ".xz",
    ".tar.xz",
}


@dataclass(frozen=True)
class ArchiveTool:
    name: str
    executable: Path
    kind: str


def is_archive(path: str | Path) -> bool:
    candidate = Path(path)
    lower_name = candidate.name.casefold()
    return candidate.suffix.casefold() in ARCHIVE_EXTENSIONS or any(
        lower_name.endswith(ext) for ext in ARCHIVE_EXTENSIONS if ext.count(".") > 1
    )


def _existing_file(path: str | Path | None) -> Path | None:
    if not path:
        return None
    candidate = Path(path)
    if candidate.is_file():
        return candidate
    return None


def _dedupe(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        try:
            key = str(path.resolve()).casefold()
        except OSError:
            key = str(path).casefold()
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def _tool_from_7zip_path(path: Path) -> ArchiveTool | None:
    if path.name.casefold() in {"7zfm.exe", "7zg.exe"}:
        cli = path.with_name("7z.exe")
        if cli.is_file():
            return ArchiveTool("7-Zip", cli, "7z")
        cli = path.with_name("7za.exe")
        if cli.is_file():
            return ArchiveTool("7-Zip", cli, "7z")
        return None
    if path.name.casefold() in {"7z.exe", "7za.exe"}:
        return ArchiveTool("7-Zip", path, "7z")
    return None


def archive_tool_from_path(path: str | Path) -> ArchiveTool | None:
    candidate = _existing_file(path)
    if not candidate:
        return None
    return _tool_from_7zip_path(candidate)


def find_archive_tools() -> list[ArchiveTool]:
    tools: list[ArchiveTool] = []

    seven_zip_candidates: list[Path] = []
    bundled_7zip = materialize_tool_dir("7zip")
    fallback_7zip = resource_path("vendor", "tools", "7zip")
    for directory in (bundled_7zip, fallback_7zip):
        for exe_name in ("7z.exe", "7za.exe", "7zFM.exe", "7zG.exe"):
            seven_zip_candidates.append(directory / exe_name)

    for path in _dedupe(seven_zip_candidates):
        existing = _existing_file(path)
        if not existing:
            continue
        tool = _tool_from_7zip_path(existing)
        if tool:
            tools.append(tool)
            break

    return tools


def preferred_archive_tool() -> ArchiveTool | None:
    tools = find_archive_tools()
    return tools[0] if tools else None


def archive_tools_summary() -> str:
    tools = find_archive_tools()
    if not tools:
        return "未找到项目内置 7-Zip；普通 zip/epub 仍可使用 Python 内置方式解压，rar/7z 需要重新打包内置工具。"
    return json.dumps(
        [{"name": t.name, "kind": t.kind, "path": str(t.executable)} for t in tools],
        ensure_ascii=False,
        indent=2,
    )


def _run(args: list[str], timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def _extract_with_7zip(tool: ArchiveTool, archive_path: Path, output_dir: Path, password: str | None) -> None:
    args = [str(tool.executable), "x", "-y", f"-o{output_dir}", str(archive_path)]
    if password:
        args.insert(3, f"-p{password}")
    result = _run(args)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(detail or f"7-Zip 解压失败: {archive_path.name}")


def _extract_zip_builtin(archive_path: Path, output_dir: Path, password: str | None) -> None:
    pwd = password.encode("utf-8") if password else None
    with zipfile.ZipFile(archive_path) as zf:
        output_root = output_dir.resolve()
        for info in zf.infolist():
            target = (output_dir / info.filename).resolve()
            if not str(target).casefold().startswith(str(output_root).casefold()):
                raise RuntimeError(f"压缩包包含不安全路径: {info.filename}")
            zf.extract(info, output_dir, pwd=pwd)


def extract_archive(
    archive_path: str | Path,
    output_dir: str | Path,
    password: str | None = None,
    tool: ArchiveTool | None = None,
    log: Logger | None = None,
) -> Path:
    archive = Path(archive_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    selected_tool = tool or preferred_archive_tool()

    if selected_tool:
        emit(log, f"使用 {selected_tool.name} 解压: {archive.name}")
        if selected_tool.kind == "7z":
            _extract_with_7zip(selected_tool, archive, output, password)
            return output

    if archive.suffix.casefold() in {".zip", ".cbz", ".epub"}:
        emit(log, f"使用 Python 内置 zip 解压: {archive.name}")
        _extract_zip_builtin(archive, output, password)
        return output

    raise RuntimeError("未找到项目内置 7-Zip；请重新打包并确认 vendor/tools/7zip 中包含 7z.exe 和 7z.dll。")
