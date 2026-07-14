from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUILD_ENV = ROOT / ".build_venv"
VENDOR_7ZIP = ROOT / "vendor" / "tools" / "7zip"
VENDOR_FFMPEG = ROOT / "vendor" / "tools" / "ffmpeg"
VENDOR_FFMPEG_ARCHIVE = VENDOR_FFMPEG / "ffmpeg.7z"
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


def run(args: list[str], cwd: Path = ROOT, timeout: int | None = None) -> None:
    print(">>> " + " ".join(args))
    env = os.environ.copy()
    env["PIP_CACHE_DIR"] = str(ROOT / ".cache" / "pip")
    env["PYINSTALLER_CONFIG_DIR"] = str(ROOT / ".cache" / "pyinstaller")
    env["TEMP"] = str(ROOT / "temp")
    env["TMP"] = str(ROOT / "temp")
    Path(env["PIP_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(env["PYINSTALLER_CONFIG_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(env["TEMP"]).mkdir(parents=True, exist_ok=True)
    subprocess.run(args, cwd=cwd, check=True, env=env, timeout=timeout)


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
    shutil.copy2(source, target)
    print(f"Vendored FFmpeg from: {source}")


def ensure_vendor_ffmpeg_archive() -> None:
    source = VENDOR_FFMPEG / "ffmpeg.exe"
    seven_zip = VENDOR_7ZIP / "7z.exe"
    if not source.exists():
        raise SystemExit("Bundled FFmpeg source is missing before archive creation.")
    if VENDOR_FFMPEG_ARCHIVE.exists() and VENDOR_FFMPEG_ARCHIVE.stat().st_mtime >= source.stat().st_mtime:
        return

    VENDOR_FFMPEG_ARCHIVE.unlink(missing_ok=True)
    run(
        [
            str(seven_zip),
            "a",
            "-t7z",
            "-mx=9",
            "-m0=lzma2",
            "-md=256m",
            "-mfb=273",
            "-mmt=on",
            str(VENDOR_FFMPEG_ARCHIVE),
            str(source),
        ],
        timeout=600,
    )
    if not VENDOR_FFMPEG_ARCHIVE.exists():
        raise SystemExit("7-Zip finished without creating the bundled FFmpeg archive.")
    print(f"Compressed bundled FFmpeg: {VENDOR_FFMPEG_ARCHIVE}")


def rerun_inside_venv() -> None:
    python_path = ensure_venv()
    run([str(python_path), str(Path(__file__).resolve())])


def smoke_test() -> None:
    run([sys.executable, "-B", str(ROOT / "smoke_test.py")])


def build_exe() -> Path:
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
        "--exclude-module",
        "PIL.AvifImagePlugin",
        "--exclude-module",
        "PIL._avif",
        "--add-data",
        str(VENDOR_7ZIP) + ";vendor/tools/7zip",
        "--add-data",
        str(VENDOR_FFMPEG_ARCHIVE) + ";vendor/tools/ffmpeg",
        str(ROOT / "app.py"),
    ]
    run(args)
    output_exe = ROOT / "dist" / f"{build_name}.exe"
    if not output_exe.exists():
        raise SystemExit(f"Build finished but exe was not found: {output_exe}")
    print(f"\nDONE: {output_exe}")
    print(f"SIZE: {output_exe.stat().st_size / 1024 / 1024:.1f} MB")
    return output_exe


def probe_built_exe(executable: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="exe_probe_", dir=ROOT / "temp") as probe_value:
        probe_dir = Path(probe_value)
        probe_executable = probe_dir / executable.name
        shutil.copy2(executable, probe_executable)
        marker = probe_dir / "startup.ok"
        env = os.environ.copy()
        env["ZIPMKV_STARTUP_PROBE"] = str(marker)
        env["ZIPMKV_PROBE_TOOLS"] = "1"
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        process = subprocess.Popen(
            [str(probe_executable)],
            cwd=probe_dir,
            env=env,
            creationflags=creationflags,
        )
        try:
            return_code = process.wait(timeout=60)
        except subprocess.TimeoutExpired as exc:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    check=False,
                    capture_output=True,
                )
            else:
                process.kill()
            raise SystemExit("Built EXE startup probe timed out before the first page became ready.") from exc

        if return_code != 0:
            raise SystemExit(f"Built EXE startup probe exited with code {return_code}.")
        marker_value = marker.read_text(encoding="utf-8").strip() if marker.exists() else "missing"
        if marker_value != "ready":
            raise SystemExit(f"Built EXE startup probe failed: {marker_value}")
        if not (probe_dir / "tools" / "ffmpeg" / "ffmpeg.exe").exists():
            raise SystemExit("Built EXE did not materialize its bundled FFmpeg.")
        if not (probe_dir / "tools" / "7zip" / "7z.exe").exists():
            raise SystemExit("Built EXE did not materialize its bundled 7-Zip.")
    print("EXE STARTUP PROBE PASSED")


def main() -> None:
    ensure_vendor_7zip()
    if not in_build_venv():
        rerun_inside_venv()
        return
    install_dependencies(Path(sys.executable))
    ensure_vendor_ffmpeg()
    ensure_vendor_ffmpeg_archive()
    smoke_test()
    output_exe = build_exe()
    probe_built_exe(output_exe)


if __name__ == "__main__":
    main()
