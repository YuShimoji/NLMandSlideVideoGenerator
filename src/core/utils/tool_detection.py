from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional


def _get_program_files_dirs() -> list[Path]:
    dirs: list[Path] = []
    for env_name in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
        env_value = os.getenv(env_name, "").strip()
        if not env_value:
            continue
        p = Path(env_value)
        if p.exists():
            dirs.append(p)

    seen: set[Path] = set()
    unique: list[Path] = []
    for d in dirs:
        if d not in seen:
            unique.append(d)
            seen.add(d)
    return unique


def _program_files_candidates(rel_paths: list[str]) -> list[Path]:
    candidates: list[Path] = []
    for base in _get_program_files_dirs():
        for rel in rel_paths:
            candidates.append(base / rel)
    return candidates


def find_executable(candidates: list[Path], env_var: str, which_names: list[str]) -> Optional[Path]:
    env_value = os.getenv(env_var, "").strip()
    if env_value:
        p = Path(env_value)
        if p.exists():
            return p

    for name in which_names:
        found = shutil.which(name)
        if found:
            p = Path(found)
            if p.exists():
                return p

    for p in candidates:
        if p.exists():
            return p

    return None


def find_autohotkey_exe() -> Optional[Path]:
    candidates = _program_files_candidates(
        [
            "AutoHotkey/AutoHotkey.exe",
            "AutoHotkey/v2/AutoHotkey.exe",
        ]
    )
    return find_executable(
        candidates=candidates,
        env_var="AUTOHOTKEY_EXE",
        which_names=["AutoHotkey.exe", "autohotkey"],
    )


def find_ymm4_exe() -> Optional[Path]:
    candidates = _program_files_candidates(["YMM4/YMM4.exe"]) + [
        Path("D:/Program Files/YMM4/YMM4.exe"),
    ]
    return find_executable(
        candidates=candidates,
        env_var="YMM4_EXE",
        which_names=["YMM4.exe"],
    )


def find_ffmpeg_exe() -> Optional[Path]:
    candidates = [
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/tools/ffmpeg/bin/ffmpeg.exe"),
        Path("/usr/bin/ffmpeg"),
        Path("/usr/local/bin/ffmpeg"),
    ] + _program_files_candidates(["ffmpeg/bin/ffmpeg.exe"])
    return find_executable(
        candidates=candidates,
        env_var="FFMPEG_EXE",
        which_names=["ffmpeg", "ffmpeg.exe"],
    )
