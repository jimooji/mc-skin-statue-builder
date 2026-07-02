# MC Skin Statue Builder

将 Minecraft 皮肤 PNG 文件转换为游戏内雕像建筑投影（Litematica `.litematic` 格式）的命令行工具。

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 功能特性

- **皮肤解析**：支持 64×64（Steve/Alex）、64×32（旧版）、128×128（高清）格式
- **自动颜色映射**：将皮肤像素智能匹配到最接近的 Minecraft 方块
- **3D 雕像生成**：根据皮肤纹理构建精确的立体雕像（含内层+外层）
- **Litematica 输出**：直接生成 `.litematic` 文件，可在游戏内加载投影
- **多种调色板**：支持羊毛、混凝土、陶瓦等 50+ 方块类型
- **可配置**：色彩空间、填充策略、底座、方块白名单等

## 快速开始

### 安装

```bash
pip install mc-skin-statue-builder
```

或从源码安装：

```bash
git clone https://github.com/jimooji/mc-skin-statue-builder.git
cd mc-skin-statue-builder
pip install -e .
```

### 使用

```bash
# 基础用法：将皮肤转换为雕像
mc-skin-statue skin.png -o statue.litematic

# 指定 Alex 纤细模型
mc-skin-statue skin.png -o statue.litematic --model alex

# 仅使用羊毛和混凝土方块
mc-skin-statue skin.png -o statue.litematic --palette wool,concrete

# 使用 Lab 色彩空间获得更精确的颜色匹配
mc-skin-statue skin.png -o statue.litematic --color-space lab

# 生成预览图
mc-skin-statue skin.png -o statue.litematic --preview preview.png
```

### 游戏内使用

1. 将生成的 `.litematic` 文件放入 `.minecraft/schematics/` 文件夹
2. 在游戏中按 `M` 打开 Litematica 菜单
3. 选择 `Load Schematics` → 找到你的雕像文件 → `Load`
4. 按 `M` 调整位置，按 `M + P` 激活 `Printer` 快速建造（创造模式）

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-o, --output` | 输出文件路径 | 必需 |
| `--model` | 模型类型：`steve`/`alex`/`auto` | `auto` |
| `--palette` | 方块调色板：`wool`/`concrete`/`terracotta`/`all` | `all` |
| `--color-space` | 色彩空间：`rgb`/`lab`/`hsv` | `rgb` |
| `--fill-inner` | 内部填充：`air`/`stone`/`concrete` | `air` |
| `--pedestal` | 底座高度（方块数） | `0` |
| `--preview` | 生成预览图路径 | 无 |
| `--scale` | 缩放比例（仅整数倍） | `1` |

## 技术细节

### 皮肤解析

支持标准 Minecraft 皮肤 UV 映射：
- 头部：8×8×8（含外层 9×9×9）
- 身体：8×12×4（含外层）
- 手臂：4×12×4（Steve）或 3×12×4（Alex）
- 腿部：4×12×4

### 颜色映射

工具预定义了 50+ 方块的基础颜色：
- 16 色羊毛、混凝土、陶瓦
- 自然方块（泥土、石头、沙子等）
- 金属方块（金、铁、钻石等）
- 特殊方块（石英、雪、蘑菇等）

映射算法：
- **RGB**：欧几里得距离，计算快
- **Lab**：CIEDE2000 色差，人眼感知更准确（需安装 `scikit-image`）
- **HSV**：色调饱和度优先，适合色彩鲜明皮肤

### 3D 雕像生成

1. 从皮肤 UV 提取每个部位的 6 面纹理
2. 将像素映射为方块，构建表面层
3. 叠加外层（帽子、衣袖、裤腿等）
4. 内部按策略填充（默认空心，节省材料）
5. 输出 Litematica NBT 格式

## 开发

### 项目结构

```
mc-skin-statue-builder/
├── src/mc_skin_statue/
│   ├── cli.py              # 命令行入口
│   ├── skin_parser.py      # 皮肤解析器
│   ├── block_palette.py    # 方块颜色映射
│   ├── statue_builder.py   # 3D 雕像生成
│   ├── litematica_writer.py # Litematica 输出
│   └── data/
│       └── block_colors.json
├── tests/                  # 单元测试
├── examples/               # 使用示例
└── PLAN.md                 # 完整技术方案
```

### 本地开发

```bash
pip install -e ".[dev,lab,preview]"
pytest
```

## 贡献

欢迎 Issue 和 PR！请查看 `PLAN.md` 了解完整技术方案。

## 许可

MIT License
