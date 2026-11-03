"""Scan a batch of per-child photo folders and build a caption manifest skeleton.

The poster renderer is deterministic and has no AI capability: it never looks at
the photos to invent text. Someone has to supply one caption per photo. This
script prepares that job: it scans the folders, enforces the supported photo
count, and writes a manifest skeleton whose `captions` arrays are exactly the
right length but empty, ready to be filled in.

Usage
-----
    python src/make_manifest.py --root input/十一月 --month 11月 --year-month 2026_11

Then open the generated JSON, replace each "" with a 10-20 character Chinese
caption, and run:

    python src/batch_main.py --root input/十一月 --manifest <generated file>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from utils import SUPPORTED_IMAGE_EXTS, load_json, project_root, save_json, scan_images


MIN_PHOTOS = 8
MAX_PHOTOS = 11
CAPTION_MIN = 10
CAPTION_MAX = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成批处理文案清单骨架")
    parser.add_argument("--root", required=True, help="包含各宝贝照片文件夹的目录")
    parser.add_argument("--month", default="11月", help="月份标签，如 11月")
    parser.add_argument("--year-month", default="2026_11", help="用于输出文件名的年月")
    parser.add_argument("--batch-dir", default=None, help="config 下的子目录名，默认 batch_<year_month>")
    parser.add_argument("--out", default=None, help="输出清单路径，默认 config/<month>_manifest.json")
    parser.add_argument(
        "--check",
        default=None,
        help="只校验一个已有清单的文案是否已填齐，不写文件",
    )
    return parser.parse_args()


def child_folders(root: Path) -> list[Path]:
    return sorted(
        [p for p in root.iterdir() if p.is_dir()],
        key=lambda p: p.name.lower(),
    )


def count_chars(text: str) -> int:
    """Count Chinese caption characters, ignoring punctuation and spaces."""
    return sum(1 for ch in text if ch.isalnum())


def build_skeleton(root: Path, month: str, year_month: str, batch_dir: str) -> dict:
    children: dict[str, dict] = {}
    for folder in child_folders(root):
        files = scan_images(folder)
        children[folder.name] = {
            "important": [],
            "summary": "",
            "captions": [""] * len(files),
            "_photo_files": [p.name for p in files],
        }
    return {
        "month": month,
        "year_month": year_month,
        "batch_dir": batch_dir,
        "seed_base": int(year_month.replace("_", "")),
        "summary_default": f"把{month}的小小快乐认真收藏起来",
        "children": children,
    }


def validate(manifest: dict, root: Path, strict_captions: bool) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for a manifest. Empty captions count as errors only when strict."""
    errors: list[str] = []
    warnings: list[str] = []
    for name, data in manifest["children"].items():
        folder = root / name
        if not folder.is_dir():
            errors.append(f"{name}: 照片目录不存在 {folder}")
            continue
        files = scan_images(folder)
        captions = data.get("captions", [])
        if not MIN_PHOTOS <= len(files) <= MAX_PHOTOS:
            errors.append(
                f"{name}: 照片 {len(files)} 张，仅支持 {MIN_PHOTOS}-{MAX_PHOTOS} 张"
            )
        if len(captions) != len(files):
            errors.append(f"{name}: 文案 {len(captions)} 条，照片 {len(files)} 张，数量不一致")
            continue

        for index, caption in enumerate(captions, start=1):
            if not caption.strip():
                if strict_captions:
                    errors.append(f"{name} 第{index}张: 文案为空")
                continue
            length = count_chars(caption)
            if not CAPTION_MIN <= length <= CAPTION_MAX:
                warnings.append(
                    f"{name} 第{index}张: 文案 {length} 字（要求 {CAPTION_MIN}-{CAPTION_MAX}）: {caption}"
                )

        for value in data.get("important", []):
            if not 1 <= int(value) <= len(files):
                errors.append(f"{name}: important 下标 {value} 越界（共 {len(files)} 张）")

        summary = data.get("summary", "")
        if summary.strip():
            length = count_chars(summary)
            if not CAPTION_MIN <= length <= CAPTION_MAX:
                warnings.append(f"{name}: 月度总结 {length} 字（要求 {CAPTION_MIN}-{CAPTION_MAX}）: {summary}")

    seen: dict[str, str] = {}
    for name, data in manifest["children"].items():
        for caption in data.get("captions", []):
            key = caption.strip()
            if not key:
                continue
            if key in seen and seen[key] != name:
                warnings.append(f"文案重复（{seen[key]} 与 {name}）: {key}")
            seen.setdefault(key, name)
    return errors, warnings


def print_check_table(manifest: dict, root: Path) -> None:
    print(f"{'宝贝':<8}{'照片':<6}{'文案已填':<10}{'重要度':<10}{'总结'}")
    print("-" * 50)
    total_filled = 0
    total_captions = 0
    for name, data in manifest["children"].items():
        files = scan_images(root / name)
        captions = data.get("captions", [])
        filled = sum(1 for c in captions if c.strip())
        total_filled += filled
        total_captions += len(captions)
        print(
            f"{name:<8}{len(files):<6}{f'{filled}/{len(captions)}':<10}"
            f"{str(data.get('important', [])):<10}{'有' if data.get('summary','').strip() else '缺'}"
        )
    print("-" * 50)
    print(f"合计: {total_filled}/{total_captions} 条文案已填写")


def main() -> int:
    args = parse_args()
    root_path = Path(args.root)
    if not root_path.is_absolute():
        root_path = (project_root() / root_path).resolve()
    if not root_path.is_dir():
        print(f"错误: 目录不存在: {root_path}", file=sys.stderr)
        return 1

    if args.check:
        manifest = load_json(Path(args.check))
        print_check_table(manifest, root_path)
        errors, warnings = validate(manifest, root_path, strict_captions=True)
    else:
        batch_dir = args.batch_dir or f"batch_{args.year_month}"
        manifest = build_skeleton(root_path, args.month, args.year_month, batch_dir)
        print_check_table(manifest, root_path)
        errors, warnings = validate(manifest, root_path, strict_captions=False)

    if warnings:
        print(f"\n警告 {len(warnings)} 条:")
        for warning in warnings:
            print(f"- {warning}")
    if errors:
        print(f"\n错误 {len(errors)} 条:")
        for error in errors:
            print(f"- {error}")
        return 1

    if not args.check:
        out = Path(args.out) if args.out else project_root() / "config" / f"{args.month}_manifest.json"
        save_json(out, manifest)
        print(f"\n骨架已写出: {out}")
        print("下一步: 把每个 \"\" 换成 10-20 字中文文案，然后运行:")
        print(f"  python src/batch_main.py --root \"{args.root}\" --manifest {out.relative_to(project_root())}")
    elif warnings:
        print(f"\n文案已填齐，但有 {len(warnings)} 条字数/重复问题待修正")
    else:
        print("\n校验通过: 所有文案已填齐且字数合规")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
