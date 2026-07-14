from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUILD_ENV = ROOT / ".build_venv"
VENDOR_7ZIP = ROOT / "vendor" / "tools" / "7zip"
VENDOR_FFMPEG = ROOT / "vendor" / "tools" / "ffmpeg"
DIST_EXE = ROOT / "dist" / "zipmkv.exe"
REQUIREMENTS_FILE = ROOT / "requirements.txt"


def build_python() -> Path:
    if os.name == "nt":
        return BUILD_ENV / "Scripts" / "python.exe"
    return BUILD_ENV / "bin" / "python"


def in_build_venv() -> bool:
    try:
        return Path(sys.executable).resolve() == build_python().resolve()
    except OSError:
        return False


def run(args: list[str], cwd: Path = ROOT) -> None:
    print(">>> " + " ".join(args))
    env = os.environ.copy()
    env["PIP_CACHE_DIR"] = str(ROOT / ".cache" / "pip")
    env["PYINSTALLER_CONFIG_DIR"] = str(ROOT / ".cache" / "pyinstaller")
    env["TEMP"] = str(ROOT / "temp")
    env["TMP"] = str(ROOT / "temp")
    Path(env["PIP_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(env["PYINSTALLER_CONFIG_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(env["TEMP"]).mkdir(parents=True, exist_ok=True)
    subprocess.run(args, cwd=cwd, check=True, env=env)


def ensure_venv() -> Path:
    python_path = build_python()
    if not python_path.exists():
        run([sys.executable, "-m", "venv", str(BUILD_ENV)])
    return python_path


def install_dependencies(python_path: Path) -> None:
    run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"])
    run(
        [
            str(python_path),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--requirement",
            str(REQUIREMENTS_FILE),
        ]
    )


def ensure_vendor_7zip() -> None:
    required = [VENDOR_7ZIP / "7z.exe", VENDOR_7ZIP / "7z.dll"]
    if all(path.exists() for path in required):
        return
    raise SystemExit(
        "Missing bundled 7-Zip. Place 7z.exe and 7z.dll under "
        "zipmkv/vendor/tools/7zip before building."
    )


def ensure_vendor_ffmpeg() -> None:
    target = VENDOR_FFMPEG / "ffmpeg.exe"
    if target.exists():
        return

    try:
        import imageio_ffmpeg

        source = Path(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception as exc:
        raise SystemExit(f"Cannot locate bundled FFmpeg from imageio-ffmpeg: {exc}") from exc

    if not source.exists():
        raise SystemExit(f"FFmpeg executable was reported but not found: {source}")

    VENDOR_FFMPEG.mkdir(parents=True, exist_ok=True)
    import shutil

    shutil.copy2(source, target)
    print(f"Vendored FFmpeg from: {source}")


def rerun_inside_venv() -> None:
    python_path = ensure_venv()
    run([str(python_path), str(Path(__file__).resolve())])


def smoke_test() -> None:
    run([sys.executable, "-B", str(ROOT / "smoke_test.py")])


def build_exe() -> None:
    build_name = "zipmkv"
    try:
        if DIST_EXE.exists():
            with DIST_EXE.open("ab"):
                pass
    except PermissionError:
        build_name = "zipmkv_new"
        print("zipmkv.exe is currently in use; building zipmkv_new.exe instead.")

    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onefile",
        "--name",
        build_name,
        "--manifest",
        str(ROOT / "zipmkv.manifest"),
        "--hidden-import",
        "image_archive_pdf.gui",
        "--hidden-import",
        "batch_archive_pdf.gui",
        "--hidden-import",
        "rename_files.gui",
        "--hidden-import",
        "xml_danmaku.gui",
        "--hidden-import",
        "subtitles.gui",
        "--hidden-import",
        "zh_convert.gui",
        "--hidden-import",
        "pypdf",
        "--hidden-import",
        "opencc",
        "--collect-data",
        "opencc",
        # FFmpeg is copied into vendor/tools above. Excluding the source package
        # prevents PyInstaller from embedding the same 84 MB binary twice.
        "--exclude-module",
        "imageio_ffmpeg",
        "--add-data",
        str(ROOT / "vendor") + ";vendor",
        str(ROOT / "app.py"),
    ]
    run(args)
    output_exe = ROOT / "dist" / f"{build_name}.exe"
    if not output_exe.exists():
        raise SystemExit(f"Build finished but exe was not found: {output_exe}")
    print(f"\nDONE: {output_exe}")
    print(f"SIZE: {output_exe.stat().st_size / 1024 / 1024:.1f} MB")


def main() -> None:
    ensure_vendor_7zip()
    if not in_build_venv():
        rerun_inside_venv()
        return
    install_dependencies(Path(sys.executable))
    ensure_vendor_ffmpeg()
    smoke_test()
    build_exe()


if __name__ == "__main__":
    main()
