"""Generate per-photo captions by sending each child's photos to a vision model.

The poster renderer itself has no AI capability: it never looks at the photos.
This module fills that gap. For every child folder under --root it sends the
photos (downscaled, originals are never touched) to an OpenAI-compatible
vision endpoint and writes the returned captions straight into the batch
manifest.

Dependencies: standard library + Pillow only. No extra pip install needed.

Usage
-----
    # 1) See what would be sent, no API call, no cost
    python src/captioner.py --root input/十一月 --out config/11月_manifest.json --dry-run

    # 2) Really generate (requires api_key in config/captioner.json
    #    or in env var WORKBUDDY_VISION_API_KEY)
    python src/captioner.py --root input/十一月 --out config/11月_manifest.json

    # 3) Resume / only top up missing captions in an existing manifest
    python src/captioner.py --root input/十月 --checkpoint config/october_manifest.json

Photos that already have a non-empty caption are skipped unless --overwrite.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from utils import project_root, save_json, scan_images
from make_manifest import MAX_PHOTOS, MIN_PHOTOS, build_skeleton, count_chars


DEFAULT_CONFIG = project_root() / "config" / "captioner.json"
ENV_KEY = "WORKBUDDY_VISION_API_KEY"


@dataclass
class VisionConfig:
    api_key: str
    base_url: str
    model: str
    timeout: int
    max_image_side: int
    jpeg_quality: int
    sleep_between_calls: float
    retries: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="调用视觉大模型为照片编写月报文案")
    parser.add_argument("--root", required=True, help="包含各宝贝照片文件夹的目录")
    parser.add_argument("--month", default="11月", help="月份标签")
    parser.add_argument("--year-month", default="2026_11", help="用于输出文件名的年月")
    parser.add_argument("--batch-dir", default=None, help="config 下的子目录名")
    parser.add_argument("--out", help="新清单写出路径")
    parser.add_argument("--checkpoint", help="已有清单路径（追加生成时优先使用）")
    parser.add_argument("--config", default=None, help="视觉模型配置，默认 config/captioner.json")
    parser.add_argument("--children", nargs="+", help="只处理指定宝贝")
    parser.add_argument("--overwrite", action="store_true", help="已填文案也重新生成")
    parser.add_argument("--per-photo", action="store_true", help="逐张提问，兼容弱模型")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要发起的请求，不调用接口")
    return parser.parse_args()


def load_vision_config(args: argparse.Namespace) -> VisionConfig:
    path = Path(args.config) if args.config else DEFAULT_CONFIG
    data: dict = {}
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
    return VisionConfig(
        api_key=(os.environ.get(ENV_KEY) or data.get("api_key") or "").strip(),
        base_url=str(data.get("base_url", "https://api.openai.com/v1/chat/completions")),
        model=str(data.get("model", "gpt-4o-mini")),
        timeout=int(data.get("timeout", 120)),
        max_image_side=int(data.get("max_image_side", 1280)),
        jpeg_quality=int(data.get("jpeg_quality", 85)),
        sleep_between_calls=float(data.get("sleep_between_calls", 0.5)),
        retries=int(data.get("retries", 2)),
    )


def encode_photo(path: Path, cfg: VisionConfig) -> str:
    """Downscale + JPEG-encode to base64. Only affects what the model sees."""
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        side = cfg.max_image_side
        img.thumbnail((side, side), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=cfg.jpeg_quality, optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def system_prompt(child_name: str, photo_count: int) -> str:
    return f"""你是一位细心的幼儿老师，正在给小朋友的成长照片写图注。
我会给你 {photo_count} 张照片，请你为每一张写一条文案。

严格规则：
1. 必须返回正好 {photo_count} 条文案，条数和照片张数完全一致，并与照片顺序一一对应。
2. 每条文案 10 到 20 个汉字（标点符号不计入字数）。宁可接近 20 字，也绝对不要少于 10 字。
3. 只写照片里肉眼确实可见的具体动作、物品或场景。
4. 禁止编造：不要写地点、日期、奖项，不要推测照片里看不到的能力或关系。
5. 不要把一次尝试写成既定能力，禁止出现"已经学会""独立完成""熟练掌握""小小XX家"这类说法。
6. 看不清具体活动时，用中性的日常表达，例如"认真摆弄手里的小教具"。
7. 文案里不要出现宝贝的姓名（{child_name}），也不要给照片里其他孩子起名字。
8. 各条之间不要重复措辞，避免用相同的词语开头或相同的句式。
9. 语气温暖自然，像家长随手记下的日记，不要写成口号。

除文案外还需要你产出：
- important：挑出 2 到 3 张最有视觉冲击力的照片序号，从 1 开始计数。
- summary：一句 10 到 20 个汉字的月度总结，概括这一个月，同样不要出现姓名。

只返回一个 JSON 对象，不要任何解释、前言或 markdown 代码块，格式如下：
{{"captions": ["第一条文案", "第二条文案"], "important": [2, 5], "summary": "月度总结"}}"""


def build_payload(base64_images: list[str], child_name: str, photo_count: int) -> list[dict]:
    """Interleave numbering markers so the model can map captions back to photos."""
    content: list[dict] = [{"type": "text", "text": f"下面是 {child_name} 的 {photo_count} 张照片，按序号排列。"}]
    for index, data in enumerate(base64_images, start=1):
        content.append({"type": "text", "text": f"第 {index} 张："})
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}})
    return content


def call_vision(cfg: VisionConfig, system: str, user_content: list[dict]) -> str:
    payload = {
        "model": cfg.model,
        "temperature": 0.7,
        "max_tokens": 2000,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        cfg.base_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=cfg.timeout) as response:
        raw = json.loads(response.read().decode("utf-8"))
    return raw["choices"][0]["message"]["content"]


def call_with_retry(cfg: VisionConfig, system: str, user_content: list[dict]) -> str:
    last_error: Exception | None = None
    for attempt in range(1, cfg.retries + 1):
        try:
            return call_vision(cfg, system, user_content)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
            last_error = exc
            print(f"    调用失败（第 {attempt}/{cfg.retries} 次）: {exc}")
            if attempt < cfg.retries:
                time.sleep(cfg.sleep_between_calls * 2)
    raise RuntimeError(f"视觉接口连续 {cfg.retries} 次调用失败: {last_error}")


def parse_reply(raw: str, photo_count: int) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    data = json.loads(text)
    captions = [str(item).strip() for item in data.get("captions", [])]
    important = [int(v) for v in data.get("important", []) if 1 <= int(v) <= photo_count]
    return {
        "captions": captions,
        "important": important[:3],
        "summary": str(data.get("summary", "")).strip(),
    }


def needs_work(child_data: dict, photo_count: int, overwrite: bool) -> bool:
    if overwrite:
        return True
    captions = child_data.get("captions", [])
    if len(captions) != photo_count:
        return True
    return any(not str(c).strip() for c in captions)


def request_child_result(name: str, files: list[Path], cfg: VisionConfig) -> dict:
    """Ask for one child's captions, retrying on transport failures or unparsable replies."""
    content = build_payload([encode_photo(p, cfg) for p in files], name, len(files))
    last_error: Exception | None = None
    for attempt in range(1, cfg.retries + 1):
        try:
            reply = call_vision(cfg, system_prompt(name, len(files)), content)
            parsed = parse_reply(reply, len(files))
            if len(parsed["captions"]) != len(files):
                raise ValueError(
                    f"模型返回 {len(parsed['captions'])} 条文案，需要 {len(files)} 条"
                )
            return parsed
        except Exception as exc:  # noqa: BLE001 - any failure here is retryable
            last_error = exc
            print(f"    第 {attempt}/{cfg.retries} 次失败: {type(exc).__name__}: {exc}")
            if attempt < cfg.retries:
                time.sleep(cfg.sleep_between_calls * 2)
    raise RuntimeError(f"{name}: 重试 {cfg.retries} 次仍失败：{last_error}。可改用 --per-photo 重试")


def process_child(name: str, files: list[Path], cfg: VisionConfig, prompt_per_photo: bool) -> dict:
    if prompt_per_photo:
        captions: list[str] = []
        for path in files:
            image = encode_photo(path, cfg)
            content = build_payload([image], name, 1)
            reply = call_with_retry(cfg, system_prompt(name, 1), content)
            parsed = parse_reply(reply, 1)
            captions.extend(parsed["captions"] or [""])
            time.sleep(cfg.sleep_between_calls)
        return {"captions": captions[: len(files)], "important": [], "summary": ""}

    return request_child_result(name, files, cfg)


def estimate_kb(files: list[Path], cfg: VisionConfig) -> float:
    """Estimate total request payload size in KB without doing a real encode."""
    total = 0.0
    for path in files:
        with Image.open(path) as img:
            w, h = img.size
        side = cfg.max_image_side
        scale = min(1.0, side / max(w, h))
        short, long_ = sorted((w * scale, h * scale))
        # Rough JPEG bytes at cfg.jpeg_quality for a natural photo.
        total += (long_ * short * 3) * 0.09
    return total / 1024


def main() -> int:
    args = parse_args()
    # Keep progress lines and error lines in the right order when piped.
    sys.stdout.reconfigure(line_buffering=True)
    root = Path(args.root)
    if not root.is_absolute():
        root = (project_root() / root).resolve()
    if not root.is_dir():
        print(f"错误: 目录不存在: {root}", file=sys.stderr)
        return 1

    cfg = load_vision_config(args)

    if args.checkpoint:
        manifest_path = Path(args.checkpoint)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_path = manifest_path.resolve()
    else:
        batch_dir = args.batch_dir or f"batch_{args.year_month}"
        manifest = build_skeleton(root, args.month, args.year_month, batch_dir)
        manifest_path = Path(args.out) if args.out else project_root() / "config" / f"{args.month}_manifest.json"
        manifest_path = manifest_path.resolve()

    # Drop internal bookkeeping fields the skeleton writes.
    for data in manifest["children"].values():
        data.pop("_photo_files", None)

    selected = args.children or list(manifest["children"])
    unknown = [name for name in selected if name not in manifest["children"]]
    if unknown:
        print(f"错误: 清单里没有这些宝贝: {', '.join(unknown)}", file=sys.stderr)
        return 1

    todo: list[tuple[str, list[Path]]] = []
    for name in selected:
        folder = root / name
        if not folder.is_dir():
            print(f"跳过 {name}: 目录不存在 {folder}")
            continue
        files = scan_images(folder)
        count = len(files)
        if not MIN_PHOTOS <= count <= MAX_PHOTOS:
            print(f"跳过 {name}: 照片 {count} 张，仅支持 {MIN_PHOTOS}-{MAX_PHOTOS} 张")
            continue
        child_data = manifest["children"][name]
        if len(child_data.get("captions", [])) != count:
            child_data["captions"] = [""] * count
        if not needs_work(child_data, count, args.overwrite):
            continue
        todo.append((name, files))

    print(f"待生成 {len(todo)} 个宝贝（共 {sum(len(f) for _, f in todo)} 张照片）")
    for name, files in todo:
        print(f"  {name}: {len(files)} 张, 请求体积约 {estimate_kb(files, cfg):.0f} KB, "
              f"模式={'逐张' if args.per_photo else '整批'}")

    if not todo:
        print("\n没有需要生成的文案（已有文案均已填写）。需要重新生成请加 --overwrite。")
        return 0

    if args.dry_run:
        print("\n[dry-run] 未发起任何请求。")
        print(f"接口地址: {cfg.base_url}")
        print(f"模型: {cfg.model}")
        return 0

    if not cfg.api_key:
        print("\n错误: 没有配置 api_key。", file=sys.stderr)
        print("请在 config/captioner.json 里填写 api_key，", file=sys.stderr)
        print(f"或设置环境变量 {ENV_KEY}。", file=sys.stderr)
        print("填好之后先跑一次 --dry-run 确认体积与孩子名单，再正式生成。", file=sys.stderr)
        return 1

    failed: list[str] = []
    for order, (name, files) in enumerate(todo, start=1):
        print(f"[{order}/{len(todo)}] {name}: 正在生成...")
        if not args.per_photo:
            time.sleep(cfg.sleep_between_calls)
        try:
            result = process_child(name, files, cfg, args.per_photo)
        except Exception as exc:  # noqa: BLE001 - one bad child must not abort the batch
            print(f"    跳过 {name}: {exc}")
            failed.append(name)
            continue
        manifest["children"][name]["captions"] = result["captions"]
        if result["important"]:
            manifest["children"][name]["important"] = result["important"]
        if result["summary"]:
            manifest["children"][name]["summary"] = result["summary"]
        bad = [c for c in result["captions"] if not 10 <= count_chars(c) <= 20]
        flag = f"，{len(bad)} 条字数越界" if bad else ""
        print(f"    完成 {len(result['captions'])} 条{flag}")
        save_json(manifest_path, manifest)

    print(f"\n已写出清单: {manifest_path}")
    if failed:
        print(f"以下 {len(failed)} 个宝贝生成失败，文案留空待补: {', '.join(failed)}")
        print("补完后重跑同一条命令即可，已有文案会自动跳过。")
    print("下一步建议先校验一遍，再生成海报:")
    print(f"  python src/make_manifest.py --root \"{args.root}\" --check {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
