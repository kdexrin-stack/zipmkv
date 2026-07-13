from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from common.log import Logger, emit
from common.text_utils import natural_sorted, safe_stem


@dataclass(frozen=True)
class RenamePair:
    source_name_file: Path | None
    target_file: Path
    new_path: Path


@dataclass(frozen=True)
class ManualRenameRule:
    prefix: str = ""
    suffix: str = ""
    number_style: str = "ep01"
    start: int = 1
    step: int = 1
    custom_template: str = ""


@dataclass
class RenameResult:
    success: int = 0
    failed: int = 0
    skipped: int = 0


def build_pairs(name_files: list[str | Path], target_files: list[str | Path]) -> list[RenamePair]:
    a_sorted = [Path(path) for path in natural_sorted([Path(p) for p in name_files])]
    b_sorted = [Path(path) for path in natural_sorted([Path(p) for p in target_files])]
    limit = min(len(a_sorted), len(b_sorted))
    pairs: list[RenamePair] = []
    for index in range(limit):
        name_source = a_sorted[index]
        target = b_sorted[index]
        new_name = name_source.stem + target.suffix
        pairs.append(RenamePair(name_source, target, target.with_name(new_name)))
    return pairs


def format_manual_name(index: int, rule: ManualRenameRule) -> str:
    number = rule.start + index * rule.step
    if rule.number_style == "1":
        middle = str(number)
    elif rule.number_style == "01":
        middle = f"{number:02d}"
    elif rule.number_style == "001":
        middle = f"{number:03d}"
    elif rule.number_style == "ep1":
        middle = f"ep{number}"
    elif rule.number_style == "ep01":
        middle = f"ep{number:02d}"
    elif rule.number_style == "EP01":
        middle = f"EP{number:02d}"
    elif rule.number_style == "E01":
        middle = f"E{number:02d}"
    elif rule.number_style == "自定义模板":
        middle = render_custom_template(rule.custom_template, number)
    else:
        middle = f"ep{number:02d}"
    return safe_stem(f"{rule.prefix}{middle}{rule.suffix}")


def render_custom_template(template: str, number: int) -> str:
    template = template.strip()
    if not template:
        return f"ep{number:02d}"
    values = {
        "n": number,
        "num": number,
        "index": number,
        "raw": number,
        "02": f"{number:02d}",
        "03": f"{number:03d}",
        "ep": f"ep{number}",
        "ep02": f"ep{number:02d}",
        "EP02": f"EP{number:02d}",
    }
    try:
        return template.format(**values)
    except Exception:
        return template.replace("{n}", str(number)).replace("{num}", str(number))


def build_manual_pairs(target_files: list[str | Path], rule: ManualRenameRule) -> list[RenamePair]:
    targets = [Path(path) for path in natural_sorted([Path(p) for p in target_files])]
    pairs: list[RenamePair] = []
    for index, target in enumerate(targets):
        new_name = format_manual_name(index, rule) + target.suffix
        pairs.append(RenamePair(None, target, target.with_name(new_name)))
    return pairs


def rename_by_pairs(pairs: list[RenamePair], log: Logger | None = None) -> RenameResult:
    result = RenameResult()
    for pair in pairs:
        old_path = pair.target_file
        new_path = pair.new_path

        if old_path.resolve() == new_path.resolve():
            emit(log, f"跳过: {old_path.name} 无需修改")
            result.skipped += 1
            continue

        if new_path.exists():
            try:
                same_file = os.path.samefile(old_path, new_path)
            except OSError:
                same_file = False
            if not same_file:
                emit(log, f"失败: {old_path.name} -> {new_path.name}，目标已存在")
                result.failed += 1
                continue

        try:
            old_path.rename(new_path)
            emit(log, f"成功: {old_path.name} -> {new_path.name}")
            result.success += 1
        except Exception as exc:
            emit(log, f"失败: {old_path.name} -> {new_path.name}，{exc}")
            result.failed += 1
    return result


def copy_by_pairs(
    pairs: list[RenamePair],
    output_dir: str | Path | None = None,
    log: Logger | None = None,
) -> RenameResult:
    result = RenameResult()
    for pair in pairs:
        source = pair.target_file
        target_dir = Path(output_dir) if output_dir else source.parent / "重命名输出"
        target_dir.mkdir(parents=True, exist_ok=True)
        new_path = target_dir / pair.new_path.name

        if new_path.exists():
            emit(log, f"失败: {source.name} -> {new_path.name}，目标已存在")
            result.failed += 1
            continue

        try:
            shutil.copy2(source, new_path)
            emit(log, f"成功复制: {source.name} -> {new_path}")
            result.success += 1
        except Exception as exc:
            emit(log, f"失败: {source.name} -> {new_path.name}，{exc}")
            result.failed += 1
    return result
