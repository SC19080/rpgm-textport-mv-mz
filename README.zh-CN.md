# RPGM TextPort — RPG Maker MV/MZ

[English](README.md) | **简体中文**

**面向 RPG Maker MV/MZ 游戏的离线文本导出 / 导入工具。**

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)](#环境要求)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

RPGM TextPort **不会**向游戏注入代码、挂钩运行时，也不会修改可执行文件。它直接读写游戏中的明文 JSON 数据文件：

1. **导出**所有支持的文本到一个 JSON 文件（或拆分为多个分片）：`{"原文": ""}`
2. 用你喜欢的方式翻译这些值（LLM、CAT 工具、手动编辑等）
3. **导入**翻译后的 JSON，写回 `data/*.json`

重启游戏后即可看到翻译后的文本。

> **独立项目。** RPGM TextPort 与 Enterbrain、Degica、KADOKAWA 或任何其他 RPG Maker 厂商均无关联，也未获得其认可或赞助。本项目同样与任何其他游戏修改器、翻译器或修改工具无关。“RPG Maker”是其各自权利人的商标。
>
> **不包含任何游戏数据。** 本仓库只包含工具本身。你必须拥有你所翻译的游戏。

> **要翻译 VX Ace 游戏？** 请使用 [RPGM TextPort 的 VX Ace 版本](https://github.com/<your-username>/rpgm-textport-vx-ace)。

---

## 为什么选择这个工具？

- **不注入、不挂钩运行时。** 游戏可执行文件不会被改动。
- **无网络访问。** 所有操作都在本地完成。
- **无外部依赖。** 只使用 Python 标准库。
- **JSON 格式简单。** 便于用 LLM 或 CAT 工具批量翻译。
- **默认更安全。** 导入支持 `--dry-run`，写入前会自动创建带时间戳的备份。
- **易于审计。** 只有一个可读的 Python 文件，没有编译组件。

因此，RPGM TextPort 非常适合小型、标准、未加密的 MV/MZ 游戏，尤其是当你希望完全掌控翻译流程时。

---

## 环境要求

- **Python 3.8+**（只使用标准库，无需 `pip install`）。
- Windows、macOS 或 Linux。RPG Maker 游戏通常以 Windows 为目标平台。
- 游戏必须使用**明文、未加密**的 RPG Maker MV/MZ `data/*.json`。
- 对游戏目录有写入权限。

已在 Windows 上使用 Python 3.14.6 测试。

如果系统无法识别 `python`，在 Windows 上可以尝试 `py`，或从 <https://www.python.org/> 安装 Python。

---

## 安装

将本仓库下载为 ZIP（**Code → Download ZIP**）或克隆仓库，然后解压到任意位置。无需安装任何依赖包。

```bat
cd /d "C:\Tools\rpgm-textport-mv-mz"
python rpgm_textport_mv_mz.py --version
```

预期输出：

```text
rpgm-textport-mv-mz 0.1.0
```

---

## 快速开始

在包含 `rpgm_textport_mv_mz.py` 的目录中打开终端。

确认工具能找到游戏：

```bat
python rpgm_textport_mv_mz.py info "C:\Games\MyGame"
```

导出文本：

```bat
python rpgm_textport_mv_mz.py export "C:\Games\MyGame" -o "C:\Translations\MyGame\strings.json"
```

翻译 `strings.json` 中的**值**。不要修改键名。

在不写入任何文件的情况下检查导入：

```bat
python rpgm_textport_mv_mz.py import "C:\Games\MyGame" "C:\Translations\MyGame\strings.json" --dry-run
```

正式应用翻译：

```bat
python rpgm_textport_mv_mz.py import "C:\Games\MyGame" "C:\Translations\MyGame\strings.json"
```

导入前请关闭游戏，导入后重新启动游戏。

---

## 定位游戏目录

以下路径都可以传给 `info`、`export` 或 `import`：

- 包含 `Game.exe` 和 `data\` 的游戏根目录
- 包含 `Game.exe` 和 `www\data\` 的游戏根目录
- `www` 目录本身
- `data` 目录本身
- 某些打包游戏使用的 `resources\app` 或 `resources\app\www` 布局

工具会查找 `data/System.json`，并报告检测到的路径。

示例：

```bat
python rpgm_textport_mv_mz.py info "C:\Games\MyGame"
python rpgm_textport_mv_mz.py info "C:\Games\MyGame\www"
python rpgm_textport_mv_mz.py info "C:\Games\MyGame\www\data"
```

如果多个游戏嵌套在同一个目录下，请传入具体的游戏目录，而不是它们的父目录。

如果工具找不到 `data/System.json`，游戏可能已加密、已打包进可执行文件、使用了非标准布局，或者根本不是 RPG Maker MV/MZ 游戏。

---

## 命令

### `info`

```bat
python rpgm_textport_mv_mz.py info "C:\Games\MyGame"
```

显示检测到的引擎、游戏目录、程序目录、`data` 目录、数据文件数量以及插件 JS 文件数量。

建议先运行此命令，确认工具找到了正确的目录。

---

### `export`

```bat
python rpgm_textport_mv_mz.py export "C:\Games\MyGame" -o "strings.json"
```

选项：

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| `-o`, `--output` | `rpgm_textport_mv_mz_strings.json` | 输出 JSON 文件。相对路径相对于当前目录。 |
| `--split N` | `0`（不拆分） | 按每片最多 `N` 条原文拆分为多个文件，便于分批翻译。 |

示例：

```bat
:: 单个输出文件
python rpgm_textport_mv_mz.py export "C:\Games\MyGame" -o "out\strings.json"

:: 每 500 条拆分为一个分片
python rpgm_textport_mv_mz.py export "C:\Games\MyGame" -o "out\strings.json" --split 500
```

使用 `--split 500` 时，输出文件命名为：

```text
strings.part001.json
strings.part002.json
...
```

如果原文条数小于或等于分片大小，则只会生成一个普通的 `strings.json`。

只有当导出确实生成多个分片时，才会删除匹配 `strings.part*.json` 的旧分片文件。普通导出，或拆分后仍只生成一个文件的 `--split` 请求，不会删除旧分片。因此，如果你改回单文件模式，请手动删除遗留的分片文件。

如果未找到可翻译文本，导出命令会以退出码 `1` 结束。

---

### `import`

```bat
python rpgm_textport_mv_mz.py import "C:\Games\MyGame" "strings.json"
```

选项：

| 选项 | 说明 |
| --- | --- |
| `--dry-run` | 读取并统计所有内容，但不写入文件，也不创建备份。 |
| `--no-backup` | 不创建 `_rpgm_textport_mv_mz_backup` 目录。**不推荐。** |

示例：

```bat
:: 先检查
python rpgm_textport_mv_mz.py import "C:\Games\MyGame" "strings.json" --dry-run

:: 正式应用
python rpgm_textport_mv_mz.py import "C:\Games\MyGame" "strings.json"

:: 从目录导入所有翻译好的分片文件
python rpgm_textport_mv_mz.py import "C:\Games\MyGame" "out\"
```

传入目录时，工具会合并该目录下直接包含的所有 `*.json` 文件。请只把翻译好的 JSON 文件放在该目录中；同一目录下的其他 `.json` 文件也会被读取。如果同一原文在不同文件中的译文不一致，工具会打印警告，并以最后读取到的译文为准。

即使部分原文没有翻译，导入命令也会以退出码 `0` 结束。请检查 `未命中` 数量和游戏中的实际文本。

---

### 帮助与版本

```bat
python rpgm_textport_mv_mz.py --help
python rpgm_textport_mv_mz.py export --help
python rpgm_textport_mv_mz.py import --help
python rpgm_textport_mv_mz.py --version
```

---

## 翻译文件格式

推荐使用扁平的 JSON 对象：

```json
{
  "こんにちは": "你好",
  "勇者よ、目を覚ませ。": "勇者啊，醒醒。"
}
```

导出文件中的值为空：

```json
{
  "こんにちは": "",
  "勇者よ、目を覚ませ。": ""
}
```

填写这些值，并保持键名与导出时完全一致。

导入器还支持：

```json
{
  "strings": {
    "こんにちは": "你好"
  }
}
```

以及数组形式：

```json
[
  {
    "text": "こんにちは",
    "translation": "你好"
  }
]
```

数组形式支持的原文键：

- `text`
- `原文`
- `source`

支持的译文键：

- `translation`
- `译文`
- `target`
- `zh`

规则：

- 文件保存为 **UTF-8**（BOM 可选）。
- 只使用标准 JSON：不要写注释，不要留尾随逗号。
- **不要翻译键名。** 键名是用于匹配的精确原文。
- 不要在键名中添加或删除空格、换行。
- 空值、仅含空白字符的值，或与原文相同的值会被忽略。这些条目可能会在导入摘要中显示为“未命中”，这是正常现象。
- 如果同一原文出现在多个位置，所有位置都会使用同一条译文。导出结果不包含上下文。
- 多行对话会导出为一个键，原文各行之间用 `\n` 分隔。在译文中使用 `\n` 来控制换行。

包含多行消息和控制符的示例：

```json
{
  "こんにちは、勇者よ。\n今日はいい天気ですね。": "你好，勇者。\n今天天气真好。",
  "\\C[1]勇者\\C[0]よ、%1 の準備はできた？": "\\C[1]勇者\\C[0]啊，%1 准备好了吗？"
}
```

在 JSON 中，字面反斜杠必须写成 `\\`。导出文件已经自动处理了这一点。如果你手动编辑译文，请保留 `\C[1]`、`\N[1]` 等控制符的双反斜杠。

仓库中提供了可直接使用的 LLM 提示词模板：
[`translation_prompt.txt`](translation_prompt.txt)。

---

## 使用大语言模型翻译

1. 导出文本。对于大型游戏，建议使用 `--split` 控制每个文件的大小：

   ```bat
   python rpgm_textport_mv_mz.py export "C:\Games\MyGame" -o "out\strings.json" --split 500
   ```

2. 打开 `translation_prompt.txt`，填写顶部的四个占位符，然后连同导出的文件一起交给 LLM。
3. 将翻译后的 JSON 保存到单独的目录中。保持键名不变。
4. 检查人名、术语和控制符。
5. 先运行 `import --dry-run`，确认无误后再正式导入。

不要让模型翻译 JSON 键名、字段名或控制符。

---

## 文本处理方式

### 对话与事件文本

工具支持标准的 RPG Maker 事件指令：

| 指令 | 含义 | 处理方式 |
| --- | --- | --- |
| `101` + `401` | 显示文本 | 连续的 `401` 行会用 `\n` 合并。 |
| `105` + `405` | 显示滚动文本 | 连续的 `405` 行会用 `\n` 合并。 |
| `102` | 显示选项 | 每个选项字符串都会被翻译。 |
| `402` | 当 [选项] | 显示用的选项标签会被翻译。 |
| `101` 第 5 个参数 | MZ 说话人名字 | 存在时会被翻译。 |
| `320` | 更改名字 | 名字字符串会被翻译。 |
| `324` | 更改昵称 | 昵称字符串会被翻译。 |
| `325` | 更改简介 | 简介字符串会被翻译。 |

导入时，译文会按 `\n` 拆分，并自动调整 `401` 或 `405` 指令的数量。因此，译文可以使用比原文更多或更少的行数。

注释（`108`/`408`）、脚本指令（`355`/`655`）和插件指令（`356`/`657`）**不会**被翻译。

### 数据库、系统和地图文本

| 文件 | 处理的字段 |
| --- | --- |
| `Actors.json` | `name`、`nickname`、`profile` |
| `Classes.json` | `name` |
| `Skills.json` | `name`、`description`、`message1`、`message2` |
| `Items.json` | `name`、`description` |
| `Weapons.json` | `name`、`description` |
| `Armors.json` | `name`、`description` |
| `Enemies.json` | `name` |
| `States.json` | `name`、`message1` … `message4` |
| `System.json` | `gameTitle`、`currencyUnit`、`terms.basic`、`terms.commands`、`terms.params`、`terms.messages`、`elements`、`skillTypes`、`weaponTypes`、`armorTypes`、`equipTypes` |
| `MapInfos.json` | `name` |
| `Map*.json` | `displayName`、事件页指令列表 |
| `CommonEvents.json` | 事件指令列表 |
| `Troops.json` | 战斗事件页指令列表 |

### 会提取哪些原文

提取器只考虑包含**假名或 CJK 表意文字**的字符串。这主要面向日文游戏。目标语言不受限制；译文可以是中文、英文，或游戏字体能够显示的任何语言。

由此产生的结果：

- 日文对话、人名和术语会被提取。
- 中文文本也会被提取，因为汉字属于 CJK。
- **纯英文文本不会被提取。**
- 纯韩文（谚文）文本不会被提取。
- 如果游戏已经完整翻译成中文，再次运行 `export` 时，其中的中文文本会再次被导出。

目前没有 `--source-language` 选项。

### 不处理的内容

- `js/plugins.js` 中的插件参数
- `js/plugins/*.js` 中硬编码的文本
- 插件使用的 `note` 和 `meta` 字段
- 图片、音频和视频中的文字
- 运行时生成的文本
- 加密或打包的游戏数据
- 自定义数据格式或非标准 JSON 结构
- 字体（参见下文“中文字符显示为方框”）

---

## 备份与还原

写入之前，导入器会创建：

```text
<游戏目录>\_rpgm_textport_mv_mz_backup\<YYYYMMDD-HHMMSS>\
```

只有实际发生变化的文件会被复制到那里。备份会保留相对路径，例如：

```text
_rpgm_textport_mv_mz_backup\20261106-004535\www\data\Map001.json
```

备份目录中的 `manifest.json` 会记录时间、工具版本、游戏目录、更改的文件、替换次数和总替换次数。

**没有自动还原命令。** 如需还原，请将备份文件按原路径复制回游戏目录。

Windows PowerShell 示例：

```powershell
$game = "C:\Games\MyGame"
$backup = "$game\_rpgm_textport_mv_mz_backup\20261106-004535"
Copy-Item -Recurse -Force "$backup\*" $game
```

这会还原被修改的数据文件。它还会把 `manifest.json` 复制到游戏根目录；该文件无害，可以删除。

注意事项：

- 备份只覆盖发生变化的 `data/*.json` 文件。
- **存档文件不会被备份。** 如有需要，请单独备份存档。
- `--no-backup` 会跳过备份。不推荐使用。
- 如果游戏目录是只读的（例如位于 `Program Files` 下），备份或写入可能会失败。请将游戏复制到可写目录，或以足够的权限运行终端。

---

## 安全清单

1. 导入前**关闭游戏**。
2. 首次测试时，先复制一份游戏目录。
3. 先运行 `export` 和 `import --dry-run`。
4. 将翻译 JSON 放在游戏的 `data\` 目录之外。
5. 导入后重新启动游戏。
6. 在游戏内测试对话、菜单、战斗消息和长文本。
7. 在确认满意之前，保留生成的备份。

RPGM TextPort 不会改动存档、可执行文件、图片、音频或 JavaScript。它只写入受支持的 `data/*.json` 文件。

---

## 故障排查

| 现象 | 可能原因 / 解决方法 |
| --- | --- |
| `[x] 没找到 data/System.json` | 目录错误，或游戏已加密/打包。尝试游戏根目录、`www` 或 `www\data`。 |
| `[!] 没有提取到任何文本` | 游戏可能只有英文、已经是非 CJK 语言，或已加密。提取器只处理假名/CJK 文本。 |
| 游戏仍显示日文 | 游戏没有重启；修改了错误的 `data` 目录；或译文为空/与原文相同。检查导入摘要（`替换次数`、`待写文件`）。 |
| 出现大量 `未命中` | 键名不完全匹配；译文为空或与原文相同；或这些字符串不在支持的字段中。 |
| `无法读取翻译文件` | 路径错误、JSON 无效，或文件不是 UTF-8 编码。请保存为 UTF-8 并校验 JSON。 |
| JSON 错误 / 尾随逗号 | 翻译文件不是有效的标准 JSON。删除注释和尾随逗号。 |
| 中文字符显示为方框 | 游戏字体缺少中文字形。RPGM TextPort 只修改文本，不修改字体。请使用字体修复插件，或替换为包含所需字形的游戏字体。 |
| 文本超出消息窗口 | 在译文中添加 `\n` 来拆分长行。工具不会根据窗口宽度自动换行。 |
| 控制符消失 | 请原样保留 `\C[1]`、`\N[1]`、`\V[1]`、`%1` 等。在 JSON 中，字面反斜杠要写成 `\\`。查看导入时的占位符警告。 |
| 导入后游戏崩溃 | 还原备份，然后运行 `--dry-run` 并检查翻译文件。确认 JSON 有效，且行数和结构看起来正确。 |
| 权限被拒绝 | 游戏目录是只读或受保护的。请将游戏复制到可写目录，或使用适当的权限。 |
| 控制台输出乱码 | 终端编码与 UTF-8 不一致。在 Windows 上先运行 `chcp 65001`，或使用 Windows Terminal。 |

### 占位符检查范围

当原文和译文中的方括号控制符或 `%n` 占位符不一致时，导入器会发出警告，例如 `\C[1]`、`\N[1]`、`\V[1]`、`%1`。

它**不会**检查所有 RPG Maker 控制符。以下控制符不在校验范围内：

- `\G`
- `\.`
- `\|`
- `\!`
- `\>`
- `\<`
- `\^`
- `\\`

该警告仅用于提示；译文仍会被写入。

---

## 读懂控制台输出

状态消息为中文。常见标签：

| 标签 | 含义 |
| --- | --- |
| `引擎` | 检测到的引擎 |
| `游戏目录` | 游戏目录 |
| `程序目录` | 程序目录（包含 `data` 和 `js`） |
| `data 目录` | 正在编辑的 data 目录 |
| `扫描文件` | 已扫描的数据文件 |
| `唯一文本` | 唯一的原文条数 |
| `出现次数` | 总出现次数 |
| `导出文件` | 导出的文件 |
| `译文条数` | 过滤后的有效译文条数 |
| `替换次数` | 实际应用的替换次数 |
| `未命中` | 没有匹配到译文的访问次数 |
| `待写文件` | 将要写入 / 已写入的文件 |
| `备份目录` | 备份目录 |
| `[dry-run]` | 未写入任何文件 |

---

## 已知限制

- 仅支持标准、明文的 MV/MZ 数据。不支持加密或打包的游戏。
- 不翻译插件参数和插件中硬编码的文本。
- 导出结果不包含上下文；相同原文在所有位置共用一条译文。
- 没有源语言选择；提取器使用假名/CJK 启发式判断。
- 没有自动还原命令；请使用备份。
- 不处理字体；游戏字体可能缺少中文字形。
- 不自动换行；需要在适当位置添加 `\n`。
- 没有严格模式：占位符不一致只会警告，即使存在未命中，导入也会以 `0` 退出。
- 没有打包好的可执行文件；需要安装 Python。
- 不保证完全保留 JSON 的空白格式。工具会尽量保留紧凑格式或缩进格式，但制表符缩进和部分格式可能发生变化。
- 非常大的游戏可能需要一些时间扫描，因为每个 `data/*.json` 文件都会被读取和解析。

---

## 测试

当前版本已在 Windows + Python 3.14 上完成冒烟测试：

- 在合成的 MV/MZ 游戏上运行了 `info`、`export`、`import --dry-run` 和 `import`。
- 验证了对话、选项、数据库、系统、地图和备份输出。
- 重新读取翻译后的数据，确认 JSON 仍然有效。

---

## 设计说明

RPGM TextPort 有意设计为一个**静态**翻译工具。它从不附加到正在运行的游戏，也从不修改可执行文件。因此，工具保持小巧、易于审计，并且不依赖游戏的运行时。

如果你的游戏需要运行时文本捕获、插件感知翻译、字体修复或自动翻译引擎，请使用专门的运行时翻译工具。RPGM TextPort 专注于大多数简单 MV/MZ 游戏所附带的标准、未加密 `data/*.json` 文件。

---

## 仓库结构

```text
rpgm-textport-mv-mz/
  rpgm_textport_mv_mz.py   主脚本
  translation_prompt.txt   LLM 翻译提示词模板
  README.md                英文说明
  README.zh-CN.md          简体中文说明
  CHANGELOG.md
  LICENSE
  .gitignore
```

---

## 致谢

- **项目作者：** 本仓库所有者。
- **实现与文档协助：** OpenCode 中的 DeepSeek V4.1 Flash 1017。

本仓库在 **OpenCode 中的 DeepSeek V4.1 Flash 1017** 的帮助下完成。

---

## 许可证

MIT。详见 [LICENSE](LICENSE)。

RPG Maker 是其各自权利人的商标。本项目与任何 RPG Maker 厂商均无关联，也未获得其认可。

---

## 版本

`rpgm-textport-mv-mz 0.1.0`
