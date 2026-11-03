from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from utils import load_json, project_root, save_json, scan_images


TEMPLATE_BY_COUNT = {
    8: "template_04_eight",
    9: "template_01",
    10: "template_05_ten",
    11: "template_06_eleven",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="批量生成儿童成长月报")
    parser.add_argument("--root", help="包含宝贝照片文件夹的目录，默认使用项目上一级目录")
    parser.add_argument("--manifest", default="config/batch_manifest.json", help="批处理文案清单")
    parser.add_argument("--debug", action="store_true", help="为每个任务启用调试输出")
    parser.add_argument("--children", nargs="+", help="只生成指定宝贝，名称用空格分隔")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = project_root()
    children_root = Path(args.root).resolve() if args.root else root.parent
    manifest = load_json(root / args.manifest)
    month = str(manifest.get("month", "9月"))
    year_month = str(manifest.get("year_month", "2026_09"))
    batch_dir = str(manifest.get("batch_dir", "batch"))
    seed_base = int(manifest.get("seed_base", 202609))
    default_summary = str(manifest.get("summary_default", "把这个月的小小快乐认真收藏起来"))
    jobs_dir = root / "config" / batch_dir
    jobs_dir.mkdir(parents=True, exist_ok=True)

    all_children = manifest["children"]
    selected_names = args.children or list(all_children)
    unknown = [name for name in selected_names if name not in all_children]
    if unknown:
        raise ValueError(f"批处理清单中没有这些宝贝: {', '.join(unknown)}")

    completed: list[str] = []
    for order, child_name in enumerate(selected_names, start=1):
        child_data = all_children[child_name]
        photos_dir = children_root / child_name
        files = scan_images(photos_dir)
        captions = [str(value) for value in child_data["captions"]]
        if len(files) != len(captions):
            raise ValueError(
                f"{child_name}: 照片数量 {len(files)} 与文案数量 {len(captions)} 不一致"
            )
        template = TEMPLATE_BY_COUNT.get(len(files))
        if template is None:
            raise ValueError(f"{child_name}: 暂不支持 {len(files)} 张照片")

        important = {int(value) for value in child_data.get("important", [])}
        caption_overrides = child_data.get("caption_overrides", {})
        config = {
            "child_name": child_name,
            "month": month,
            "title": f"{child_name}宝贝成长月报",
            "summary": str(child_data.get("summary", default_summary)),
            "photos_dir": str(photos_dir),
            "reference_dir": "input/reference",
            "template": template,
            "seed": seed_base + list(all_children).index(child_name) + 1,
            "output_file": f"output/{batch_dir}/{child_name}_{year_month}_growth_monthly.png",
            "photos": [
                dict({
                    "file": path.name,
                    "caption": caption,
                    "importance": 3 if index in important else 1,
                }, **{
                    f"caption_{key}": int(value)
                    for key, value in caption_overrides.get(str(index), {}).items()
                    if key in {"x", "y", "width"}
                })
                for index, (path, caption) in enumerate(zip(files, captions), start=1)
            ],
        }
        config_path = jobs_dir / f"{child_name}.json"
        save_json(config_path, config)

        command = [sys.executable, str(root / "src" / "main.py"), "--config", str(config_path)]
        if args.debug:
            command.append("--debug")
        print(f"[{order}/{len(selected_names)}] 正在生成: {child_name}")
        subprocess.run(command, cwd=root, check=True)
        report_source = root / "output" / "render_report.json"
        report_target = root / "output" / batch_dir / f"{child_name}_render_report.json"
        shutil.copy2(report_source, report_target)
        completed.append(child_name)

    print(f"批量生成完成: {', '.join(completed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
