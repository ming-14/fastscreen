import os
import sys

# fastscreencore 包位于仓库根，加入 sys.path 以便测试导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastscreencore import CaptureEngine, TargetType, CaptureMethod
