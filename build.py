#!/usr/bin/env python
"""FastScreen 构建脚本：编译 fastscreen.dll 并安装到 fastscreencore 包内。

用法:
    python build.py          # 编译 Release DLL
    python build.py clean    # 清理构建目录与产物
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT / "build"
DLL_NAME = "fastscreen.dll"
# DLL 安装目标：fastscreencore 包目录，即 _find_dll() 默认搜索路径
INSTALL_DIR = ROOT / "fastscreencore"


def find_cmake() -> Optional[str]:
    """查找 cmake 可执行文件路径（系统 PATH 或标准安装位置）。"""
    cmake = shutil.which("cmake")
    if cmake:
        return cmake
    for base in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")):
        if not base:
            continue
        p = Path(base) / "CMake" / "bin" / "cmake.exe"
        if p.exists():
            return str(p)
    return None


def configure(cmake: str):
    """CMake 配置，尝试 VS 生成器，失败回退默认。"""
    BUILD_DIR.mkdir(exist_ok=True)
    generators = [
        "Visual Studio 18 2026",
        "Visual Studio 17 2022",
        "Visual Studio 16 2019",
    ]
    last = None
    for gen in generators:
        print(f"[cmake] 尝试生成器: {gen}")
        last = subprocess.run([cmake, "..", "-G", gen, "-A", "x64"], cwd=BUILD_DIR)
        if last.returncode == 0:
            return
    print("[cmake] 指定生成器失败，回退默认生成器")
    last = subprocess.run([cmake, ".."], cwd=BUILD_DIR)
    if last.returncode != 0:
        print("ERROR: CMake 配置失败")
        sys.exit(1)


def build(cmake: str):
    """编译 Release 配置。"""
    result = subprocess.run([cmake, "--build", ".", "--config", "Release", "-j"], cwd=BUILD_DIR)
    if result.returncode != 0:
        print("ERROR: 编译失败")
        sys.exit(1)


def locate_dll() -> Path:
    """在 CMake 构建输出目录中查找编译出的 DLL。"""
    candidates = [
        BUILD_DIR / "bin" / "Release" / DLL_NAME,
        BUILD_DIR / "bin" / DLL_NAME,
        BUILD_DIR / "Release" / DLL_NAME,
        BUILD_DIR / DLL_NAME,
    ]
    for p in candidates:
        if p.exists():
            return p
    print(f"ERROR: {DLL_NAME} 未在构建目录中找到")
    print(f"  搜索路径: {[str(p) for p in candidates]}")
    sys.exit(1)


def install():
    """复制 DLL 到 fastscreencore 包目录。"""
    src = locate_dll()
    dst = INSTALL_DIR / DLL_NAME
    shutil.copy2(src, dst)
    print(f"[install] {src} -> {dst}")


def clean():
    """清理构建目录与已安装的 DLL。"""
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        print(f"[clean] 已删除 {BUILD_DIR}")
    dll = INSTALL_DIR / DLL_NAME
    if dll.exists():
        dll.unlink()
        print(f"[clean] 已删除 {dll}")


def main():
    parser = argparse.ArgumentParser(description="编译 FastScreen C++ 引擎 DLL")
    parser.add_argument(
        "action", nargs="?", default="build",
        choices=["build", "clean"],
        help="操作（默认 build）",
    )
    args = parser.parse_args()

    if args.action == "clean":
        clean()
        return

    cmake = find_cmake()
    if not cmake:
        print("ERROR: 未找到 cmake，请从 https://cmake.org/download/ 安装")
        sys.exit(1)

    configure(cmake)
    build(cmake)
    install()
    print("构建完成！")


if __name__ == "__main__":
    main()