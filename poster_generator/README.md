# 儿童成长月报自动排版生成工具

这是一个确定性的儿童成长月报海报生成器。它读取 9 张儿童原始照片和 JSON 文案配置，用 Python + Pillow 做传统图层合成，输出 A4 竖版 PNG。

本项目不使用任何生成式图片模型，不做 AI 修脸、美颜、调色、去噪、超分、背景替换或照片重绘。照片只会经历 EXIF 方向修正、等比例缩放、轻微旋转、圆角蒙版、边框和普通图层合成。

## 安装

```bash
cd poster_generator
pip install -r requirements.txt
```

如果系统没有 Python，请先安装 Python 3.10+，并确保 `python` 命令可用。

## 目录

```text
poster_generator/
  input/
    reference/       # 放1张风格参考图，仅供人工查看，程序不拼接其像素
    photos/          # 放9张儿童原始照片
  output/            # 输出PNG、debug图和render_report.json
  assets/
    textures/
    stickers/
  fonts/             # 可放合法可用的中文字体 .ttf/.otf
  templates/
    growth_monthly_blue.json
  src/
    main.py
    config_loader.py
    image_loader.py
    layout_engine.py
    photo_renderer.py
    text_renderer.py
    decoration_renderer.py
    background_renderer.py
    validation.py
    exporter.py
    utils.py
  example_config.json
  requirements.txt
  README.md
```

## 放照片

把 9 张照片放入：

```text
input/photos/
```

推荐命名：

```text
01.jpg
02.jpg
...
09.jpg
```

支持 `jpg`、`jpeg`、`png`、`webp`。照片目录必须正好 9 张图片，否则程序停止生成，不会自动复制补位。

## 放参考图

把参考图放入：

```text
input/reference/
```

参考图只用于理解风格，不参与最终 PNG 像素合成。程序不会从参考图裁剪背景、人物、文字或贴纸。

## 配置

编辑 `example_config.json`：

```json
{
  "child_name": "小六",
  "month": "9月",
  "title": "小六宝贝成长月报",
  "summary": "把九月的小小快乐都认真收藏起来",
  "template": "template_01",
  "seed": 202609,
  "photos": [
    {
      "file": "01.jpg",
      "caption": "认真体验游戏里的每一个有趣瞬间",
      "importance": 3
    }
  ]
}
```

`importance` 支持：

- `1` 普通照片
- `2` 中等照片
- `3` 重点照片

布局引擎会把重点照片优先分配到较大的照片槽位。

## 运行

```bash
python src/main.py --config example_config.json
```

开启调试：

```bash
python src/main.py --config example_config.json --debug
```

调试模式会输出：

- `output/debug_layout.png`
- 每张照片的槽位、尺寸、旋转角度和文案区域

## 输出

默认输出：

```text
output/xiaoliu_2026_09_growth_monthly.png
output/render_report.json
```

PNG 尺寸为 `2480 × 3508`，保存 `300 DPI` 元数据。

`render_report.json` 会记录：

- 最终尺寸
- 照片数量
- 每张照片原文件
- 原始宽高
- 最终显示尺寸
- 缩放比例
- 旋转角度
- 是否裁剪
- caption
- 使用模板
- seed
- 校验警告

## 切换模板

在配置文件中修改：

```json
"template": "template_02"
```

当前提供：

- `template_01`
- `template_02`
- `template_03`

## 字体

程序会先搜索 `fonts/` 目录中的 `.ttf` 和 `.otf` 字体，再搜索 Windows 常见中文字体：

- Microsoft YaHei
- SimHei
- SimSun
- KaiTi

如果中文显示成方框，请把合法可用的中文字体放入 `fonts/` 目录。

## 新增底贴样式

修改 `src/text_renderer.py` 的 `render_caption_note()`：

- 增加新的 `style` 分支
- 使用 Pillow 绘制不规则纸片、圆角便签、胶带、星星或爱心
- 不要把文字画到照片层里

然后在 `templates/growth_monthly_blue.json` 的照片槽位里设置：

```json
"caption_style": "note_yellow"
```

## 新增照片卡片样式

修改 `src/photo_renderer.py` 的 `render_photo_card()`：

- 增加新的 `frame_type` 分支
- 只给照片外围添加纸片、白边、胶带、阴影和装饰
- 不要对照片内部使用滤镜、调色、增强、锐化、去噪或 AI 接口

然后在模板中设置：

```json
"frame_type": "blue_backing"
```

## 替换下一批照片

1. 清空 `input/photos/`
2. 放入新的 9 张照片，命名为 `01.jpg` 到 `09.jpg`
3. 修改 `example_config.json` 中的姓名、月份、标题、总结和每张照片文案
4. 运行：

```bash
python src/main.py --config example_config.json
```

相同照片、配置、模板和 seed 会产生稳定输出。
