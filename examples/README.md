# MC Skin Statue Builder - Examples

## CLI 使用示例

### 基础转换

```bash
mc-skin-statue my_skin.png -o my_statue.litematic
```

### 使用 Alex 纤细模型

```bash
mc-skin-statue alex_skin.png -o alex_statue.litematic --model alex
```

### 仅使用混凝土方块（更鲜艳）

```bash
mc-skin-statue skin.png -o statue.litematic --palette concrete
```

### 使用 Lab 色彩空间 + 多种方块

```bash
mc-skin-statue skin.png -o statue.litematic \
  --palette wool,concrete,terracotta \
  --color-space lab
```

### 添加底座 + 实心填充

```bash
mc-skin-statue skin.png -o statue.litematic \
  --pedestal 2 \
  --fill-inner stone
```

### 生成预览图

```bash
mc-skin-statue skin.png -o statue.litematic --preview preview.png
```

## Python API 示例

参见 `build_statue.py`：

```python
from mc_skin_statue.skin_parser import SkinParser
from mc_skin_statue.block_palette import BlockPalette
from mc_skin_statue.statue_builder import StatueBuilder
from mc_skin_statue.litematica_writer import LitematicaWriter

# 1. 解析皮肤
parser = SkinParser("skin.png")
parts = parser.get_all_parts()

# 2. 选择调色板
palette = BlockPalette(categories=["wool", "concrete"], color_space="rgb")

# 3. 构建雕像
builder = StatueBuilder(palette=palette, pedestal_height=1)
statue = builder.build(parts)

# 4. 输出文件
writer = LitematicaWriter()
writer.write("Main", statue, builder.get_palette_with_air(), "statue.litematic")
```

## 游戏内使用

1. 将 `.litematic` 文件放入 `.minecraft/schematics/`
2. 进入 Minecraft，按 `M` 打开 Litematica 菜单
3. 选择 `Load Schematics` → 找到你的文件 → `Load`
4. 按 `M` 调整位置，放置 `Schematic Placement`
5. 创造模式：按 `M + P` 使用 `Printer` 自动建造
6. 生存模式：按 `M + L` 查看材料清单，手动按投影建造

## 高级技巧

### 皮肤获取

- 从 [NameMC](https://namemc.com) 下载任意玩家的皮肤
- 从 Minecraft 官方启动器导出当前皮肤
- 使用 [MinersOnline](https://miners.online) 批量下载

### 优化雕像效果

- **颜色鲜艳的卡通风格皮肤**：使用 `concrete` 调色板
- **写实/柔和色调皮肤**：使用 `wool,terracotta` 调色板
- **金属/科幻风格**：添加 `metal` 到调色板
- **大面积纯色区域**：Lab 色彩空间通常更精确

### 自定义方块颜色

编辑 `src/mc_skin_statue/data/block_colors.json` 添加自定义方块和颜色值。
