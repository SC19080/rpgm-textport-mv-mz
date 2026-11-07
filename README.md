# RPGM TextPort — RPG Maker MV/MZ

**English** | [简体中文](README.zh-CN.md)

**Offline text extractor / importer for RPG Maker MV/MZ games.**

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)](#requirements)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

RPGM TextPort does **not** inject into the game, hook the runtime, or modify
executables. It reads and writes the game's plain JSON data files directly:

1. **export** all supported text into one JSON file (or split parts):
   `{"original": ""}`
2. translate the values with your own method (LLM, CAT tool, manual editing,
   etc.)
3. **import** the translated JSON back into `data/*.json`

The game then displays the translated text after it is restarted.

> **Independent project.** RPGM TextPort is not affiliated with, endorsed by,
> or sponsored by Enterbrain, Degica, KADOKAWA, or any other RPG Maker vendor.
> It is also not affiliated with any other game trainer, translator, or
> modification tool. “RPG Maker” is a trademark of its respective owners.
>
> **No game data is included.** This repository contains only the tool. You
> must own the games you translate.

> **Translating a VX Ace game?** Use the VX Ace edition of RPGM TextPort.

---

## Why this tool?

- **No injection, no runtime hooks.** The game executable is never touched.
- **No network access.** Everything happens locally.
- **No external dependencies.** Only the Python standard library is used.
- **Simple JSON format.** Easy to batch-translate with an LLM or a CAT tool.
- **Safe by default.** Import supports `--dry-run` and creates a timestamped
  backup before writing.
- **Auditable.** One readable Python file, no compiled components.

This makes RPGM TextPort a good fit for small, standard, unencrypted MV/MZ
games where you want full control over the translation process.

---

## Requirements

- **Python 3.8+** (only the standard library is used; no `pip install` needed).
- Windows, macOS, or Linux. Windows is the usual target for RPG Maker games.
- The game must use **plain, unencrypted** RPG Maker MV/MZ `data/*.json`.
- Write permission to the game folder.

Tested with Python 3.14.6 on Windows.

If `python` is not recognized, try `py` on Windows, or install Python from
<https://www.python.org/>.

---

## Installation

Download this repository as a ZIP (**Code → Download ZIP**) or clone it, then
extract it anywhere. No package installation is required.

```bat
cd /d "C:\Tools\rpgm-textport-mv-mz"
python rpgm_textport_mv_mz.py --version
```

Expected output:

```text
rpgm-textport-mv-mz 0.1.0
```

---

## Quick start

Open a terminal in the folder containing `rpgm_textport_mv_mz.py`.

Check that the game is detected:

```bat
python rpgm_textport_mv_mz.py info "C:\Games\MyGame"
```

Export the text:

```bat
python rpgm_textport_mv_mz.py export "C:\Games\MyGame" -o "C:\Translations\MyGame\strings.json"
```

Translate the **values** in `strings.json`. Do not change the keys.

Check the import without writing anything:

```bat
python rpgm_textport_mv_mz.py import "C:\Games\MyGame" "C:\Translations\MyGame\strings.json" --dry-run
```

Apply the translation:

```bat
python rpgm_textport_mv_mz.py import "C:\Games\MyGame" "C:\Translations\MyGame\strings.json"
```

Close the game before importing, then restart it after importing.

---

## Finding the game folder

You can pass any of these to `info`, `export`, or `import`:

- the game root containing `Game.exe` and `data\`
- the game root containing `Game.exe` and `www\data\`
- the `www` folder itself
- the `data` folder itself
- a `resources\app` or `resources\app\www` layout used by some packaged games

The tool searches for `data/System.json` and reports the detected paths.

Examples:

```bat
python rpgm_textport_mv_mz.py info "C:\Games\MyGame"
python rpgm_textport_mv_mz.py info "C:\Games\MyGame\www"
python rpgm_textport_mv_mz.py info "C:\Games\MyGame\www\data"
```

If several games are nested under one folder, pass the exact game folder rather
than the parent folder.

If the tool cannot find `data/System.json`, the game may be encrypted, packed
into an executable, using a non-standard layout, or not an RPG Maker MV/MZ game.

---

## Commands

### `info`

```bat
python rpgm_textport_mv_mz.py info "C:\Games\MyGame"
```

Shows the detected engine, game folder, application folder, `data` folder,
number of data files, and the number of plugin JS files.

Use this first to confirm the tool found the right folder.

---

### `export`

```bat
python rpgm_textport_mv_mz.py export "C:\Games\MyGame" -o "strings.json"
```

Options:

| Option | Default | Meaning |
| --- | --- | --- |
| `-o`, `--output` | `rpgm_textport_mv_mz_strings.json` | Output JSON file. Relative paths are relative to the current directory. |
| `--split N` | `0` (no split) | Split into files of at most `N` source strings. Useful for batch translation. |

Examples:

```bat
:: one output file
python rpgm_textport_mv_mz.py export "C:\Games\MyGame" -o "out\strings.json"

:: split into parts of 500 strings
python rpgm_textport_mv_mz.py export "C:\Games\MyGame" -o "out\strings.json" --split 500
```

With `--split 500`, the output files are named:

```text
strings.part001.json
strings.part002.json
...
```

If the number of strings is less than or equal to the split size, one normal
`strings.json` is produced instead.

Older part files matching `strings.part*.json` are removed only when the export
actually creates multiple parts. A plain export, or a `--split` request that
fits into one file, does not remove old part files, so delete stale parts
manually if you switch back to a single file.

The export command exits with code `1` if no translatable text was found.

---

### `import`

```bat
python rpgm_textport_mv_mz.py import "C:\Games\MyGame" "strings.json"
```

Options:

| Option | Meaning |
| --- | --- |
| `--dry-run` | Read and count everything, but write no files and create no backup. |
| `--no-backup` | Do not create the `_rpgm_textport_mv_mz_backup` folder. **Not recommended.** |

Examples:

```bat
:: check first
python rpgm_textport_mv_mz.py import "C:\Games\MyGame" "strings.json" --dry-run

:: apply
python rpgm_textport_mv_mz.py import "C:\Games\MyGame" "strings.json"

:: import all translated split files from a folder
python rpgm_textport_mv_mz.py import "C:\Games\MyGame" "out\"
```

When a directory is passed, all `*.json` files directly inside it are merged.
Place only the translated JSON files in that directory; other `.json` files in
the same directory will also be read. If the same source string has different
translations in different files, a warning is printed and the last one read
wins.

The import command exits with code `0` even when some strings were not
translated. Check the `未命中` (“misses”) count and the actual game text.

---

### Help and version

```bat
python rpgm_textport_mv_mz.py --help
python rpgm_textport_mv_mz.py export --help
python rpgm_textport_mv_mz.py import --help
python rpgm_textport_mv_mz.py --version
```

---

## Translation file format

The recommended format is a flat JSON object:

```json
{
  "こんにちは": "你好",
  "勇者よ、目を覚ませ。": "勇者啊，醒醒。"
}
```

The exported file uses empty values:

```json
{
  "こんにちは": "",
  "勇者よ、目を覚ませ。": ""
}
```

Fill in the values and keep the keys exactly as they were exported.

The importer also accepts:

```json
{
  "strings": {
    "こんにちは": "你好"
  }
}
```

and an array form:

```json
[
  {
    "text": "こんにちは",
    "translation": "你好"
  }
]
```

Supported source keys in the array form:

- `text`
- `原文`
- `source`

Supported translation keys:

- `translation`
- `译文`
- `target`
- `zh`

Rules:

- Save the file as **UTF-8** (BOM optional).
- Use standard JSON only: no comments, no trailing commas.
- **Do not translate the keys.** The key is the exact original text used for
  matching.
- Do not add or remove whitespace or newlines in the keys.
- A value that is empty, only whitespace, or identical to the source is ignored.
  Such entries can appear as “misses” in the import summary; that is normal.
- If the same original string occurs in several places, one translation is used
  everywhere. Context is not included in the export.
- Multi-line dialogue is exported as one key with `\n` between the original
  lines. Use `\n` in the translation to control line breaks.

Example with a multi-line message and a control code:

```json
{
  "こんにちは、勇者よ。\n今日はいい天気ですね。": "你好，勇者。\n今天天气真好。",
  "\\C[1]勇者\\C[0]よ、%1 の準備はできた？": "\\C[1]勇者\\C[0]啊，%1 准备好了吗？"
}
```

In JSON, a literal backslash must be written as `\\`. The exported file already
does this. If you hand-edit a translation, keep the double backslashes for
control codes such as `\C[1]` and `\N[1]`.

A ready-to-use LLM prompt template is included in
[`translation_prompt.txt`](translation_prompt.txt).

---

## Translating with an LLM

1. Export the text. For large games, use `--split` to keep each file manageable:

   ```bat
   python rpgm_textport_mv_mz.py export "C:\Games\MyGame" -o "out\strings.json" --split 500
   ```

2. Open `translation_prompt.txt`, fill in the four placeholders at the top, and
   give it to your LLM together with the exported file(s).
3. Save the translated JSON in a separate folder. Keep the keys unchanged.
4. Review names, terminology, and control codes.
5. Run `import --dry-run` first, then import for real.

Never let the model translate the JSON keys, field names, or control codes.

---

## How text is processed

### Dialogue and event text

The tool handles standard RPG Maker event commands:

| Code | Meaning | Handling |
| --- | --- | --- |
| `101` + `401` | Show Text | Consecutive `401` lines are merged with `\n`. |
| `105` + `405` | Show Scrolling Text | Consecutive `405` lines are merged with `\n`. |
| `102` | Show Choices | Each choice string is translated. |
| `402` | When [choice] | The displayed choice label is translated. |
| `101` 5th parameter | MZ speaker name | Translated when present. |
| `320` | Change Name | Name string is translated. |
| `324` | Change Nickname | Nickname string is translated. |
| `325` | Change Profile | Profile string is translated. |

During import, translated text is split on `\n` and the number of `401` or `405`
commands is adjusted automatically. A translation can therefore use more or
fewer lines than the original.

Comments (`108`/`408`), script commands (`355`/`655`), and plugin commands
(`356`/`657`) are **not** translated.

### Database, system, and map text

| File | Fields handled |
| --- | --- |
| `Actors.json` | `name`, `nickname`, `profile` |
| `Classes.json` | `name` |
| `Skills.json` | `name`, `description`, `message1`, `message2` |
| `Items.json` | `name`, `description` |
| `Weapons.json` | `name`, `description` |
| `Armors.json` | `name`, `description` |
| `Enemies.json` | `name` |
| `States.json` | `name`, `message1` … `message4` |
| `System.json` | `gameTitle`, `currencyUnit`, `terms.basic`, `terms.commands`, `terms.params`, `terms.messages`, `elements`, `skillTypes`, `weaponTypes`, `armorTypes`, `equipTypes` |
| `MapInfos.json` | `name` |
| `Map*.json` | `displayName`, event page command lists |
| `CommonEvents.json` | event command lists |
| `Troops.json` | battle event page command lists |

### Which source strings are extracted

The extractor only considers strings containing **kana or CJK ideographs**.
This is intended for Japanese games. The target language is not restricted;
translation values can be Chinese, English, or anything else the game's font
can display.

Consequences:

- Japanese dialogue, names, and terms are extracted.
- Chinese text is also extracted, because Chinese characters are CJK.
- **English-only text is not extracted.**
- Korean Hangul-only text is not extracted.
- A game that is already fully translated to Chinese will have its Chinese text
  re-exported if you run `export` again.

There is currently no `--source-language` option.

### What is not handled

- Plugin parameters in `js/plugins.js`
- Text hard-coded in `js/plugins/*.js`
- `note` and `meta` fields used by plugins
- Images, audio, and video text
- Runtime-generated text
- Encrypted or packed game data
- Custom data formats or non-standard JSON schemas
- Fonts (see “Chinese characters appear as boxes” below)

---

## Backups and restoring

Before writing, the importer creates:

```text
<game folder>\_rpgm_textport_mv_mz_backup\<YYYYMMDD-HHMMSS>\
```

Only files that are actually changed are copied there. The backup preserves the
relative path, for example:

```text
_rpgm_textport_mv_mz_backup\20261106-004535\www\data\Map001.json
```

A `manifest.json` in the backup folder records the time, tool version, game
folder, changed files, replacement counts, and total replacements.

There is **no automatic restore command**. To restore, copy the backed-up files
back over the game, preserving their paths.

Example on Windows PowerShell:

```powershell
$game = "C:\Games\MyGame"
$backup = "$game\_rpgm_textport_mv_mz_backup\20261106-004535"
Copy-Item -Recurse -Force "$backup\*" $game
```

This restores the changed data files. It also copies `manifest.json` to the game
root; that file is harmless and can be deleted.

Notes:

- The backup covers only changed `data/*.json` files.
- **Save files are not backed up.** Back up your saves separately if needed.
- `--no-backup` skips the backup. It is not recommended.
- If the game folder is read-only (for example, under `Program Files`), the
  backup or write may fail. Copy the game to a writable folder or run the
  terminal with sufficient permissions.

---

## Safety checklist

1. **Close the game** before importing.
2. Make a copy of the game folder for the first test.
3. Run `export` and `import --dry-run` first.
4. Keep the translation JSON outside the game's `data\` folder.
5. Restart the game after importing.
6. Test dialogue, menus, battle messages, and long text in-game.
7. Keep the generated backup until you are satisfied.

RPGM TextPort does not touch save files, executables, images, audio, or
JavaScript. It only writes the supported `data/*.json` files.

---

## Troubleshooting

| Symptom | Likely cause / fix |
| --- | --- |
| `[x] 没找到 data/System.json` | Wrong folder, or the game is encrypted/packed. Try the game root, `www`, or `www\data`. |
| `[!] 没有提取到任何文本` | The game may be English-only, already in a non-CJK language, or encrypted. The extractor only handles kana/CJK text. |
| Game still shows Japanese | The game was not restarted, the wrong `data` folder was edited, or the translation values were empty/identical to the source. Check the import summary (`替换次数`, `待写文件`). |
| Many `未命中` entries | Keys do not match exactly, the translation is empty or identical to the source, or those strings are not in supported fields. |
| `无法读取翻译文件` | Wrong path, invalid JSON, or a non-UTF-8 file. Save as UTF-8 and validate the JSON. |
| JSON error / trailing comma | The translation file is not valid standard JSON. Remove comments and trailing commas. |
| Chinese characters appear as boxes | The game font lacks Chinese glyphs. RPGM TextPort only changes text, not fonts. Use a font-fix plugin or replace the game font with one that includes the required glyphs. |
| Text overflows the message window | Add `\n` to the translation to split long lines. The tool does not automatically wrap text to the window width. |
| Control codes disappeared | Keep `\C[1]`, `\N[1]`, `\V[1]`, `%1`, etc. exactly. In JSON, write a literal backslash as `\\`. Review the import's placeholder warnings. |
| Game crashes after import | Restore the backup, then run `--dry-run` and inspect the translation file. Make sure the JSON is valid and line counts/structure look correct. |
| Permission denied | The game folder is read-only or protected. Copy the game to a writable folder or use appropriate permissions. |
| Console output looks garbled | The terminal encoding does not match UTF-8. On Windows, run `chcp 65001` first or use Windows Terminal. |

### Placeholder-check coverage

The importer warns when bracketed control codes or `%n` placeholders differ
between source and translation, for example `\C[1]`, `\N[1]`, `\V[1]`, `%1`.

It does **not** check every RPG Maker control code. In particular, these are
not validated:

- `\G`
- `\.`
- `\|`
- `\!`
- `\>`
- `\<`
- `\^`
- `\\`

The warning is informational only; the translation is still written.

---

## Reading the console output

The status messages are in Chinese. Common labels:

| Label | Meaning |
| --- | --- |
| `引擎` | Detected engine |
| `游戏目录` | Game folder |
| `程序目录` | Application folder (contains `data` and `js`) |
| `data 目录` | Data folder being edited |
| `扫描文件` | Data files scanned |
| `唯一文本` | Unique source strings |
| `出现次数` | Total occurrences |
| `导出文件` | Exported file(s) |
| `译文条数` | Valid translation entries after filtering |
| `替换次数` | Replacements applied |
| `未命中` | Visits with no matching translation |
| `待写文件` | Files that will be / were written |
| `备份目录` | Backup folder |
| `[dry-run]` | No files were written |

---

## Known limitations

- Standard, plain MV/MZ data only. Encrypted or packed games are not supported.
- Plugin parameters and hard-coded plugin text are not translated.
- No context is included in the export; identical source strings share one
  translation everywhere.
- No source-language selection; the extractor uses a kana/CJK heuristic.
- No automatic restore command; use the backup.
- No font handling; Chinese glyphs may be missing from the game's font.
- No automatic line wrapping; add `\n` where needed.
- No strict mode: placeholder mismatches are warnings, and the import exits `0`
  even with misses.
- No packaged executable; Python is required.
- Exact JSON whitespace is not guaranteed. The tool tries to preserve compact
  versus indented files, but tab indentation and some formatting may change.
- Very large games may take some time to scan because every `data/*.json` file
  is read and parsed.

---

## Testing

The current release was smoke-tested on Windows with Python 3.14:

- `info`, `export`, `import --dry-run`, and `import` on a synthetic MV/MZ game.
- Verified dialogue, choices, database, system, map, and backup output.
- Re-read the translated data to confirm the JSON stayed valid.

---

## Design notes

RPGM TextPort is intentionally a **static** translator. It never attaches to a
running game and never changes an executable. That keeps the tool small, easy to
audit, and independent of the game's runtime.

If your game needs runtime text capture, plugin-aware translation, font fixes,
or automated translation engines, use a dedicated runtime translation tool
instead. RPGM TextPort focuses on the standard, unencrypted `data/*.json` files
that most simple MV/MZ games ship with.

---

## Repository layout

```text
rpgm-textport-mv-mz/
  rpgm_textport_mv_mz.py   main script
  translation_prompt.txt   LLM translation prompt template
  README.md                English
  README.zh-CN.md          Simplified Chinese
  CHANGELOG.md
  LICENSE
  .gitignore
```

---

## Credits

- **Project author:** the repository owner.
- **Implementation and documentation assistance:** DeepSeek V4.1 Flash 1017 in
  OpenCode.

This repository was prepared with the help of **DeepSeek V4.1 Flash 1017 in
OpenCode**.

---

## License

MIT. See [LICENSE](LICENSE).

RPG Maker is a trademark of its respective owners. This project is not
affiliated with or endorsed by any RPG Maker vendor.

---

## Version

`rpgm-textport-mv-mz 0.1.0`
