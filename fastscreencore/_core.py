import ctypes
import platform
from pathlib import Path
from typing import Optional

class MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_int32),
        ("name", ctypes.c_wchar * 128),
        ("left", ctypes.c_int32),
        ("top", ctypes.c_int32),
        ("width", ctypes.c_int32),
        ("height", ctypes.c_int32),
        ("primary", ctypes.c_int32),
    ]

class WindowInfo(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("title", ctypes.c_wchar * 256),
        ("class_name", ctypes.c_wchar * 256),
        ("left", ctypes.c_int32),
        ("top", ctypes.c_int32),
        ("width", ctypes.c_int32),
        ("height", ctypes.c_int32),
        ("visible", ctypes.c_int32),
    ]

class Frame(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.POINTER(ctypes.c_uint8)),
        ("width", ctypes.c_int32),
        ("height", ctypes.c_int32),
        ("stride", ctypes.c_int32),
        ("bpp", ctypes.c_int32),
        ("timestamp_ms", ctypes.c_int64),
        ("owns_data", ctypes.c_int32),
    ]

FRAME_CALLBACK = ctypes.CFUNCTYPE(None, ctypes.POINTER(Frame), ctypes.c_void_p)

class TargetType:
    MONITOR = 0
    WINDOW = 1

class CaptureMethod:
    AUTO = 0
    DXGI = 1
    WGC = 2
    BITBLT = 3

class ImageFormat:
    PNG = 0
    JPEG = 1
    BMP = 2

class ErrorCode:
    OK = 0
    NOT_INITIALIZED = -1
    INVALID_PARAM = -2
    CAPTURE_FAILED = -3
    ENCODE_FAILED = -4
    NO_OUTPUT = -5
    UNSUPPORTED = -6
    ALREADY_RUNNING = -7
    NOT_RUNNING = -8

def _arch_dir() -> str:
    """当前 Python 进程架构对应的 DLL 子目录（x64 / x86 / arm64）。

    按进程位宽判断，而非系统架构：32 位 Python 运行在 64 位系统上时
    platform.machine() 仍返回 AMD64（os.uname 模拟基于 GetNativeSystemInfo），
    因此必须用指针宽度区分 x86 与 x64。
    """
    if ctypes.sizeof(ctypes.c_void_p) == 4:
        return "x86"
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "arm64"
    return "x64"


def _find_dll() -> str:
    package_dir = Path(__file__).parent
    dll_name = "fastscreen.dll"
    arch = _arch_dir()

    search_paths = [
        package_dir / arch / dll_name,
        package_dir / dll_name,
        package_dir / "bin" / dll_name,
    ]

    # 按架构独立开发构建目录（build/<arch>/bin/Release/…）
    project_root = package_dir
    while project_root.parent != project_root:
        if (project_root / "CMakeLists.txt").exists():
            for cfg in ("Release", "Debug"):
                search_paths.extend([
                    project_root / "build" / arch / "bin" / cfg / dll_name,
                    project_root / "build" / arch / "bin" / dll_name,
                    project_root / "build" / arch / cfg / dll_name,
                    project_root / "build" / arch / dll_name,
                ])
            break
        project_root = project_root.parent

    for p in search_paths:
        p = p.resolve()
        if p.exists():
            return str(p)

    raise FileNotFoundError(
        f"Cannot find {dll_name} for architecture {arch}. Please build the C++ library first:\n"
        f"  python build.py --arch {arch}\n"
        f"Searched: {[str(p) for p in search_paths]}"
    )

class _Lib:
    _instance: Optional['_Lib'] = None

    def __init__(self):
        dll_path = _find_dll()
        self.lib = ctypes.CDLL(dll_path)
        self._setup_signatures()
        self.lib.fs_init()

    def _setup_signatures(self):
        self.lib.fs_init.restype = ctypes.c_int
        self.lib.fs_init.argtypes = []

        self.lib.fs_shutdown.restype = None
        self.lib.fs_shutdown.argtypes = []

        self.lib.fs_enum_monitors.restype = ctypes.c_int
        self.lib.fs_enum_monitors.argtypes = [
            ctypes.POINTER(ctypes.POINTER(MonitorInfo)),
            ctypes.POINTER(ctypes.c_int),
        ]

        self.lib.fs_enum_windows.restype = ctypes.c_int
        self.lib.fs_enum_windows.argtypes = [
            ctypes.POINTER(ctypes.POINTER(WindowInfo)),
            ctypes.POINTER(ctypes.c_int),
        ]

        self.lib.fs_free_enum.restype = None
        self.lib.fs_free_enum.argtypes = [ctypes.c_void_p]

        self.lib.fs_create_session.restype = ctypes.c_int64
        self.lib.fs_create_session.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]

        self.lib.fs_destroy_session.restype = ctypes.c_int
        self.lib.fs_destroy_session.argtypes = [ctypes.c_int64]

        self.lib.fs_capture_frame.restype = ctypes.c_int
        self.lib.fs_capture_frame.argtypes = [
            ctypes.c_int64, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.POINTER(Frame),
        ]

        self.lib.fs_frame_save.restype = ctypes.c_int
        self.lib.fs_frame_save.argtypes = [
            ctypes.POINTER(Frame), ctypes.c_wchar_p, ctypes.c_int, ctypes.c_float,
        ]

        self.lib.fs_frame_encode_to_buffer.restype = ctypes.c_int
        self.lib.fs_frame_encode_to_buffer.argtypes = [
            ctypes.POINTER(Frame), ctypes.c_int, ctypes.c_float,
            ctypes.POINTER(ctypes.POINTER(ctypes.c_uint8)), ctypes.POINTER(ctypes.c_int),
        ]

        self.lib.fs_frame_encode_to_buffer_scaled.restype = ctypes.c_int
        self.lib.fs_frame_encode_to_buffer_scaled.argtypes = [
            ctypes.POINTER(Frame), ctypes.c_int, ctypes.c_float,
            ctypes.c_int, ctypes.c_int,
            ctypes.POINTER(ctypes.POINTER(ctypes.c_uint8)), ctypes.POINTER(ctypes.c_int),
        ]

        self.lib.fs_free_buffer.restype = None
        self.lib.fs_free_buffer.argtypes = [ctypes.c_void_p]

        self.lib.fs_frame_copy_data.restype = ctypes.c_int
        self.lib.fs_frame_copy_data.argtypes = [
            ctypes.POINTER(Frame), ctypes.POINTER(ctypes.c_uint8), ctypes.c_int,
        ]

        self.lib.fs_frame_release.restype = None
        self.lib.fs_frame_release.argtypes = [ctypes.POINTER(Frame)]

        self.lib.fs_start_continuous.restype = ctypes.c_int
        self.lib.fs_start_continuous.argtypes = [
            ctypes.c_int64, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, FRAME_CALLBACK, ctypes.c_void_p,
        ]

        self.lib.fs_stop_continuous.restype = ctypes.c_int
        self.lib.fs_stop_continuous.argtypes = [ctypes.c_int64]

        self.lib.fs_session_is_running.restype = ctypes.c_int
        self.lib.fs_session_is_running.argtypes = [ctypes.c_int64]

    @classmethod
    def get(cls) -> '_Lib':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def shutdown(cls):
        if cls._instance is not None:
            cls._instance.lib.fs_shutdown()
            cls._instance = None

import atexit
atexit.register(_Lib.shutdown)
