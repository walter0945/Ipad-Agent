---
name: video
description: 用分镜生成视频。当用户要求"生成视频 / 做视频 / 视频素材 / 字幕卡"时使用。
---

生成视频时调用 `render_video` 工具：

- `storyboard` 传 JSON 字符串，格式：
  `{"scenes":[{"text":"画面文案","duration":秒,"bg":"#RRGGBB"}]}`
- `output` 是输出文件名（如 `video.mp4`），输出到工作区
- 每个 scene 的 text 居中渲染在纯色背景上，逐帧用 ffmpeg 合成 mp4

建议流程：先跟用户确认分镜文案与每幕时长，再一次性生成。可选参数 fps（默认 24）、width/height（默认 1280x720）。
