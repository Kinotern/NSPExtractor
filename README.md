# NSP 提取体系化工具链

## 概述

本工具链实现了 Nintendo Switch NSP 文件的自动化解包与资源提取全流程。  
从 NSP 分发包到最终可浏览的图片、可读的脚本字节码，覆盖完整的五阶段提取管线。

## 提取管线

```
NSP 文件
  │
  ├─[Stage 1] NSP → NCA 提取 (hactool -t pfs0)
  │
  ├─[Stage 2] NCA 解密 → ExeFS + RomFS (hactool + titlekey)
  │
  ├─[Stage 3] RomFS → PSB 归档提取 (PsbDecompile info-psb)  [中间步骤，不保留]
  │
  ├─[Stage 4] PSB 图片 → PNG (PsbDecompile image)
  │
  └─[Stage 5] .nut.m 脚本 → 字节码转储 (dump_nut_bytecode.py)
```

## 目录结构

```
112nsp提取体系化/
├── nsp_toolkit.py          # 主入口 (CLI / GUI)
├── setup.py                # 首次运行设置 (复制工具和密钥)
├── run.bat                 # Windows 启动器
├── dump_nut_bytecode.py    # Squirrel 字节码转储器
├── lib/                    # 核心模块
│   ├── config.py           # 配置与路径管理
│   ├── logger.py           # 日志系统
│   ├── runner.py           # 子进程执行器
│   ├── keys.py             # 密钥管理 (prod.keys / title.keys / .tik)
│   ├── nsp_extract.py      # NSP → NCA 提取
│   ├── nca_decrypt.py      # NCA 解密
│   ├── psb_extract.py      # PSB 归档提取
│   ├── image_extract.py    # 图片提取
│   ├── script_dump.py      # 脚本字节码转储
│   └── metadata.py         # 元数据生成与文件分类
├── tools/                  # 工具 (setup.py 自动复制)
│   ├── hactool.exe
│   └── PsbDecompile.exe
├── keys/                   # 密钥文件 (setup.py 自动复制)
│   ├── prod.keys
│   └── title.keys
├── out/                    # 提取输出
└── logs/                   # 运行日志
```

## 输出结构

每个 NSP 文件的提取结果保存在 `out/<NSP名称>/` 下：

```
out/
└── NEKOPARA Vol 3 [010045000E418000][v0]/
    ├── nca/                # 提取的原始 NCA 文件
    ├── exefs/              # 可执行文件系统 (main, rtld, sdk 等)
    ├── romfs/              # ROM 文件系统 (原始资源)
    ├── images/             # 转换后的 PNG 图片
    ├── scripts/            # 转储的字节码 (.txt + .json)
    └── metadata.json       # 提取元数据报告
```

PSB 归档提取（Stage 3）为中间步骤，结果不会保留到最终输出目录。

## 快速开始

### 1. 首次设置

```cmd
cd C:\Users\Kino\Desktop\nsp\112nsp提取体系化
python setup.py
```

setup.py 会自动从上级目录复制：
- `hactool.exe` → `tools/`
- `PsbDecompile.exe` → `tools/`
- `prod.keys` → `keys/`
- `title.keys` → `keys/`

### 2. 运行提取

**方式一：双击启动 (GUI 选文件)**

```
双击 run.bat
```

**方式二：命令行指定文件夹**

```cmd
python nsp_toolkit.py --folder C:\path\to\nsp\files
```

**方式三：命令行指定文件**

```cmd
python nsp_toolkit.py --files game1.nsp game2.nsp
```

**方式四：GUI 模式**

```cmd
python nsp_toolkit.py --gui
```

### 3. 选择提取阶段

默认执行全部五个阶段。可以用 `--stages` 指定只运行部分阶段：

```cmd
# 只提取 NCA 和解密
python nsp_toolkit.py --folder . --stages nca decrypt

# 只提取图片
python nsp_toolkit.py --folder . --stages image
```

可用阶段：`nca` `decrypt` `psb` `image` `script`

## 命令行参数

| 参数 | 说明 |
|------|------|
| `--folder PATH` | 指定包含 NSP 文件的文件夹 |
| `--files PATH ...` | 指定一个或多个 NSP 文件 |
| `--gui` | 打开 GUI 文件选择器 |
| `--stages STAGE ...` | 指定提取阶段 (默认: 全部) |
| `--out PATH` | 覆盖输出目录 (默认: ./out) |
| `--hactool PATH` | 覆盖 hactool.exe 路径 |
| `--psb-decompile PATH` | 覆盖 PsbDecompile.exe 路径 |
| `--prod-keys PATH` | 覆盖 prod.keys 路径 |
| `--title-keys PATH` | 覆盖 title.keys 路径 |
| `--mdf-key KEY` | MDF 密钥前缀 (默认: 38757621acf82) |
| `--mdf-key-length LEN` | MDF 密钥长度 (默认: 131) |
| `--fix-keys` | 自动修复 prod.keys 格式问题 |

## 核心模块说明

### config.py — 配置管理

管理工具路径、密钥路径、输出目录等配置。  
自动在工具链本地目录和上级目录中查找工具和密钥文件，支持命令行覆盖。

### keys.py — 密钥管理

- 加载和解析 `prod.keys` / `title.keys`
- 从 `.tik` 文件偏移 0x180 处提取 title key
- 自动修复 `mariko_master_kek_source` / `master_kek_source` 系列密钥的尾部多余 `00`

### nsp_extract.py — NSP 提取

- 使用 `hactool -t pfs0` 从 NSP 中提取 NCA 文件
- 自动识别最大的 NCA 文件（游戏主内容）
- 从 .tik 文件批量提取 title key

### nca_decrypt.py — NCA 解密

- 使用 hactool 解密 NCA 文件
- 支持 titlekey 和 basenca 参数
- 输出 ExeFS 和 RomFS 目录

### psb_extract.py — PSB 归档提取

- 自动发现 RomFS 中的 `*_info.psb.m` + `*_body.bin` 配对文件
- 使用 PsbDecompile info-psb 提取归档内容
- 支持 MDF 密钥配置
- 提取结果为中间产物，供后续 image/script 阶段使用

### image_extract.py — 图片提取

- 批量将 PSB 图片资源转换为 PNG
- 自动发现 .psb.m / .psb 文件

### script_dump.py — 脚本转储

- 批量将 .nut.m (Squirrel SQIR 字节码) 转储为可读文本和 JSON
- 保持原始目录结构

### metadata.py — 元数据生成

- 自动分类 RomFS 资源（image/script/sound/voice/scenario/motion/font/config）
- 生成 metadata.json 包含完整的提取报告
- 记录文件数量、大小、分类信息和错误

## 错误处理

- 每个阶段独立 try/except，单个文件失败不影响整体流程
- 所有错误记录到日志和 metadata.json
- hactool 的 WARN 级别输出自动识别并记录
- 子进程超时和异常退出均有处理

## 日志系统

- 日志同时输出到控制台和文件
- 日志文件保存在 `logs/` 目录，格式：`extract_YYYYMMDD_HHMMSS.log`
- DEBUG 级别记录子进程完整输出
- INFO 级别记录关键进度

## 依赖

- Python 3.10+
- hactool.exe
- PsbDecompile.exe
- prod.keys (Switch 产品密钥)
- title.keys (可选，标题密钥)

## 注意事项

1. **密钥安全**：`prod.keys` 和 `title.keys` 包含敏感信息，请勿公开分享
2. **磁盘空间**：NSP 解包后可能占用数倍原始文件大小的空间
3. **prod.keys 格式**：某些密钥文件可能包含尾部多余的 `00`，使用 `--fix-keys` 自动修复
4. **Patch RomFS**：更新包的 RomFS 是增量补丁，需要与 base 合并才能得到完整内容
5. **MDF 密钥**：默认密钥 `38757621acf82` 适用于 NEKOPARA 系列，其他游戏可能需要不同密钥
6. **中文路径**：hactool.exe 不支持中文路径，工具链自动使用 ASCII 临时工作目录处理
