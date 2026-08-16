"""视频生成工具：分镜 JSON → Pillow 逐帧渲染 → ffmpeg 合成 mp4。

storyboard 格式：{"scenes": [{"text": "标题", "duration": 秒, "bg": "#RRGGBB"}]}
依赖 Pillow（生成帧）+ ffmpeg（编码）。两者在 a-Shell 均可用。
"""

import json
import subprocess
import tempfile
from pathlib import Path
from tools import Tool

# CJK-capable 字体排在前面（也能渲染拉丁字符），避免中文渲染成豆腐块；
# 纯拉丁字体作为最后兜底。可用 render_video 的 font 参数显式指定路径。
_FONT_CANDIDATES = (
    # Windows 中文
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    # iOS / macOS 中文
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    # Linux 中文（Noto CJK）
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    # 拉丁兜底
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def _load_font(size: int, font_path: str | None = None):
    from PIL import ImageFont
    candidates = ([font_path] if font_path else []) + list(_FONT_CANDIDATES)
    for path in candidates:
        if path and Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()   # 兜底为位图字体，无法渲染中文


def _render_frames(scenes: list[dict], fps: int, width: int, height: int, out_dir: Path,
                   font_path: str | None = None) -> int:
    from PIL import Image, ImageDraw
    font = _load_font(48, font_path)
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
            n = _render_frames(scenes, fps, width, height, frames_dir, args.get("font"))
            out.parent.mkdir(parents=True, exist_ok=True)
            cmd = ["ffmpeg", "-y", "-framerate", str(fps),
                   "-i", str(frames_dir / "frame_%05d.png"),
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            except subprocess.TimeoutExpired:
                return "ffmpeg 超时（超过 300 秒），已中止"
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
            "font": {"type": "string", "description": "字体文件路径；含中文文案时建议显式指定一个 CJK 字体"},
        }, "required": ["storyboard", "output"]},
        render_video,
    )]
