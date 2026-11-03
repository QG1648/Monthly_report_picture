# 月报图片生成

这是一个用于自动生成儿童成长月报海报的本地项目。它基于 Python 和 Pillow，读取儿童照片、配置文案与模板，然后自动排版并输出高质量的 A4 竖版海报。

## 项目简介

本项目适用于以下场景：

- 儿童成长月报
- 亲子记录册海报
- 月度回顾图
- 批量生成统一风格的成长记录照片墙

它的设计目标是：

- 自动读取本地照片与配置
- 使用固定模板进行统一排版
- 输出稳定可复现的海报效果
- 不依赖在线图片服务或生成式图像模型

## 技术栈

- Python 3.10+
- Pillow
- JSON 配置
- 本地模板排版

## 目录结构

```text
月报图片/
├── README.md
├── .gitignore
├── 提示词.txt
├── 日志去水印/
├── poster_generator/
│   ├── README.md
│   ├── requirements.txt
│   ├── example_config.json
│   ├── input/
│   │   ├── photos/
│   │   ├── reference/
│   ├── output/
│   ├── assets/
│   ├── fonts/
│   ├── templates/
│   └── src/
└──
```

## 主要功能

- 读取 9 张照片并按照模板自动布局
- 支持配置姓名、月份、标题、总结和每张照片文案
- 支持多种照片层级和文本样式
- 生成 PNG 海报和渲染报告
- 适合批量替换照片后生成新一期月报

## 使用方式

详细使用说明请查看：

- [poster_generator/README.md](poster_generator/README.md)

核心运行方式如下：

```bash
cd poster_generator
pip install -r requirements.txt
python src/main.py --config example_config.json
```

## 说明

- 本项目主要用于本地生成，不适合直接上传原始照片和生成结果。
- 照片素材、输出图片、日志、缓存文件应保留在本地，不应提交到仓库。
- 代码和配置文件是项目的核心内容，适合上传和版本管理。

## 注意事项

为了保持仓库整洁并避免无关文件上传，建议：

- 不上传原始照片
- 不上传生成后的 PNG
- 不上传中间缓存、日志和临时文件
- 仅保留脚本、模板、文档和必要配置

## 许可证

本项目仅用于本地学习、创作和业务用途，具体使用请根据实际需求确认相关权限。