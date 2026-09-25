"""Cameras: frame photos and the rim check before closing.

Four cameras (two per shuttle) see each frame face from both ends at an
angle. The frame is flat, so each image is rectified with a homography
computed from the four frame corners (or the ArUco tag), then the two
halves of each face are blended. Only capture lives here; rectification and
detection run in the Gratheon image pipeline.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Protocol


class CaptureRig(Protocol):
    def capture(self, meta: Dict) -> List[str]: ...


class RimCheck(Protocol):
    def bees_on_rim(self) -> int: ...


class NullCapture:
    """Records what would have been captured (dry runs, tests)."""

    def __init__(self) -> None:
        self.shots: List[Dict] = []

    def capture(self, meta: Dict) -> List[str]:
        self.shots.append(dict(meta))
        return []


class NoRimCheck:
    def bees_on_rim(self) -> int:
        return 0


class OpenCVCapture:
    """USB/CSI cameras via OpenCV with the white strobe fired per exposure.

    `devices` maps a camera name ('left_front', ...) to an OpenCV source: an
    index for UVC cameras or a GStreamer pipeline string for CSI cameras on
    the Jetson, e.g.
      "nvarguscamerasrc sensor-id=0 ! video/x-raw(memory:NVMM),width=3280,height=2464 ! nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! appsink"
    """

    def __init__(self, devices: Dict[str, object], out_dir: str, strobe: Optional[Callable[[float], None]] = None, flash_s: float = 0.03):
        import cv2  # only needed on the robot

        self.cv2 = cv2
        self.out = Path(out_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.strobe = strobe or (lambda v: None)
        self.flash_s = flash_s
        self.cams = {}
        for name, src in devices.items():
            cap = cv2.VideoCapture(src, cv2.CAP_GSTREAMER) if isinstance(src, str) else cv2.VideoCapture(src)
            if not cap.isOpened():
                raise RuntimeError(f"camera {name} ({src}) did not open")
            self.cams[name] = cap

    def capture(self, meta: Dict) -> List[str]:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        paths = []
        for name, cap in self.cams.items():
            cap.grab()  # drop a stale buffered frame
            self.strobe(1.0)
            time.sleep(self.flash_s)
            ok, img = cap.read()
            self.strobe(0.0)
            if not ok:
                continue
            base = self.out / f"{stamp}_box{meta.get('box')}_frame{meta.get('frame')}_{name}"
            self.cv2.imwrite(str(base.with_suffix(".jpg")), img, [self.cv2.IMWRITE_JPEG_QUALITY, 92])
            base.with_suffix(".json").write_text(json.dumps({**meta, "camera": name, "time": stamp}))
            paths.append(str(base.with_suffix(".jpg")))
        return paths
