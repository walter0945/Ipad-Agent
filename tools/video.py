"""视频生成工具：分镜 JSON → Pillow 逐帧渲染 → ffmpeg 合成 mp4。

storyboard 格式：{"scenes": [{"text": "标题", "duration": 秒, "bg": "#RRGGBB"}]}
依赖 Pillow（生成帧）+ ffmpeg（编码）。两者在 a-Shell 均可用。
"""

import json
import subprocess
import tempfile
from pathlib import Path
from tools import Tool

_FONT_CANDIDATES = (
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def _load_font(size: int):
    from PIL import ImageFont
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


def _render_frames(scenes: list[dict], fps: int, width: int, height: int, out_dir: Path) -> int:
    from PIL import Image, ImageDraw
    font = _load_font(48)
    frame_no = 0
    for scene in scenes:
        text = scene.get("text", "")
        duration = float(scene.get("duration", 2.0))
        n = max(int(round(duration * fps)), 1)
        bg = scene.get("bg", "#1e1e2e")
        for _ in range(n):
            img = Image.new("RGB", (width, height), bg)
            draw = ImageDraw.Draw(img)
            draw.text((width // 2, height // 2), text, font=font, fill="white", anchor="mm")
            img.save(out_dir / f"frame_{frame_no:05d}.png")
            frame_no += 1
    return frame_no


def make_video_tools(gate) -> list[Tool]:
    def render_video(args):
        out = gate.sandbox_root.joinpath(args["output"]).resolve()
        if out.exists():
            if not gate.overwrite(out):
                return "拒绝：未确认覆盖"
        elif not gate.write(out):
            return "拒绝：未确认写入"
        try:
            data = json.loads(args["storyboard"])
        except json.JSONDecodeError as e:
            return f"storyboard 不是合法 JSON：{e}"
        scenes = data.get("scenes", [])
        if not scenes:
            return "分镜为空"
        fps = int(args.get("fps", 24))
        width = int(args.get("width", 1280))
        height = int(args.get("height", 720))
        with tempfile.TemporaryDirectory() as tmp:
            frames_dir = Path(tmp)
            n = _render_frames(scenes, fps, width, height, frames_dir)
            out.parent.mkdir(parents=True, exist_ok=True)
            cmd = ["ffmpeg", "-y", "-framerate", str(fps),
                   "-i", str(frames_dir / "frame_%05d.png"),
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                return f"ffmpeg 失败：{r.stderr[-300:]}"
        return f"已生成视频 {args['output']}（{n} 帧，{fps} fps）"

    return [Tool(
        "render_video",
        "根据分镜生成视频：storyboard 传 JSON 字符串 {\"scenes\":[{\"text\":\"文案\",\"duration\":秒,\"bg\":\"#RRGGBB\"}]}",
        {"type": "object", "properties": {
            "storyboard": {"type": "string"},
            "output": {"type": "string"},
            "fps": {"type": "integer"},
            "width": {"type": "integer"},
            "height": {"type": "integer"},
        }, "required": ["storyboard", "output"]},
        render_video,
    )]
