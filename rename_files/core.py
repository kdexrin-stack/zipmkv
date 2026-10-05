from __future__ import annotations

import os
import shutil
import uuid
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
    active: list[RenamePair] = []
    source_keys = {str(pair.target_file.resolve()).casefold() for pair in pairs}
    destination_groups: dict[str, list[RenamePair]] = {}

    for pair in pairs:
        old_path = pair.target_file
        new_path = pair.new_path
        old_key = str(old_path.resolve()).casefold()
        new_key = str(new_path.resolve()).casefold()
        if old_key == new_key:
            emit(log, f"跳过: {old_path.name} 无需修改")
            result.skipped += 1
            continue
        if not old_path.is_file():
            emit(log, f"失败: {old_path.name}，源文件不存在")
            result.failed += 1
            continue
        if new_path.exists() and new_key not in source_keys:
            emit(log, f"失败: {old_path.name} -> {new_path.name}，目标已存在")
            result.failed += 1
            continue
        destination_groups.setdefault(new_key, []).append(pair)
        active.append(pair)

    duplicate_keys = {key for key, group in destination_groups.items() if len(group) > 1}
    if duplicate_keys:
        filtered: list[RenamePair] = []
        for pair in active:
            key = str(pair.new_path.resolve()).casefold()
            if key in duplicate_keys:
                emit(log, f"失败: {pair.target_file.name} -> {pair.new_path.name}，多个文件生成同名目标")
                result.failed += 1
            else:
                filtered.append(pair)
        active = filtered

    if not active:
        return result

    # Stage every source first so A->B and B->A swaps work without overwriting.
    staged: list[tuple[RenamePair, Path]] = []
    completed: list[tuple[RenamePair, Path]] = []
    try:
        for pair in active:
            temporary = pair.target_file.with_name(
                f".zipmkv_rename_{uuid.uuid4().hex}{pair.target_file.suffix}"
            )
            pair.target_file.rename(temporary)
            staged.append((pair, temporary))
        for pair, temporary in staged:
            temporary.rename(pair.new_path)
            completed.append((pair, temporary))
    except Exception as exc:
        # Keep the operation atomic enough for a batch rename: restore every
        # source that was moved to a temporary or final destination.
        for pair, _temporary in reversed(completed):
            if pair.new_path.exists() and not pair.target_file.exists():
                try:
                    pair.new_path.rename(pair.target_file)
                except OSError:
                    pass
        for pair, temporary in reversed(staged):
            if temporary.exists() and not pair.target_file.exists():
                try:
                    temporary.rename(pair.target_file)
                except OSError:
                    pass
        emit(log, f"批量重命名失败，已尝试恢复源文件: {exc}")
        result.failed += len(active)
        return result

    for pair, _temporary in completed:
        emit(log, f"成功: {pair.target_file.name} -> {pair.new_path.name}")
    result.success += len(completed)
    return result


def copy_by_pairs(
    pairs: list[RenamePair],
    output_dir: str | Path | None = None,
    log: Logger | None = None,
) -> RenameResult:
    result = RenameResult()
    active: list[tuple[RenamePair, Path]] = []
    destination_groups: dict[str, list[RenamePair]] = {}

    # Validate the whole batch before copying anything. This keeps a typo in
    # one row from leaving a partially generated output directory.
    for pair in pairs:
        source = pair.target_file
        target_dir = Path(output_dir) if output_dir else source.parent / "重命名输出"
        new_path = target_dir / pair.new_path.name
        key = str(new_path.resolve()).casefold()
        destination_groups.setdefault(key, []).append(pair)

        if not source.is_file():
            emit(log, f"失败: {source.name}，源文件不存在")
            result.failed += 1
            continue
        active.append((pair, new_path))

    duplicate_keys = {key for key, group in destination_groups.items() if len(group) > 1}
    if duplicate_keys:
        kept: list[tuple[RenamePair, Path]] = []
        for pair, new_path in active:
            if str(new_path.resolve()).casefold() in duplicate_keys:
                emit(log, f"失败: {pair.target_file.name} -> {new_path.name}，多个文件生成同名目标")
                result.failed += 1
            else:
                kept.append((pair, new_path))
        active = kept

    if not active:
        return result

    available: list[tuple[RenamePair, Path]] = []
    for pair, new_path in active:
        if new_path.exists():
            emit(log, f"失败: {pair.target_file.name} -> {new_path.name}，目标已存在")
            result.failed += 1
        else:
            available.append((pair, new_path))
    active = available
    if not active:
        return result

    target_dirs = {new_path.parent for _pair, new_path in active}
    for target_dir in target_dirs:
        target_dir.mkdir(parents=True, exist_ok=True)

    for pair, new_path in active:
        source = pair.target_file
        try:
            shutil.copy2(source, new_path)
            emit(log, f"成功复制: {source.name} -> {new_path}")
            result.success += 1
        except Exception as exc:
            emit(log, f"失败: {source.name} -> {new_path.name}，{exc}")
            result.failed += 1
    return result
