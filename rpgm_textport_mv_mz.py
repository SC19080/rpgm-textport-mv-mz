#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# RPGM TextPort MV/MZ
# Created with assistance from DeepSeek V4.1 Flash 1017 in OpenCode.
# License: MIT
"""
RPGM TextPort MV/MZ 0.1.0 —— RPG Maker MV/MZ 文本导出 / 导入

思路：不注入、不拦截，直接读写游戏 data/*.json。
    export : 扫描游戏，把所有可翻译文本汇总成一个扁平 JSON： {"原文": ""}
    import : 读取翻译好的 JSON（"原文": "译文"），原地写回 data/*.json，并自动备份。

用法：
    python rpgm_textport_mv_mz.py info   "D:\\Games\\MyGame"
    python rpgm_textport_mv_mz.py export "D:\\Games\\MyGame" -o strings.json
    python rpgm_textport_mv_mz.py export "D:\\Games\\MyGame" -o out\\strings.json --split 500
    python rpgm_textport_mv_mz.py import "D:\\Games\\MyGame" strings.json --dry-run
    python rpgm_textport_mv_mz.py import "D:\\Games\\MyGame" strings.json
    python rpgm_textport_mv_mz.py import "D:\\Games\\MyGame" out\\      # 目录：合并全部 *.json

翻译文件格式（也是最省事的 LLM 友好格式）：
    {
        "こんにちは": "你好",
        "勇者よ、目を覚ませ。": "勇者啊，醒醒。"
    }
也兼容 [{"text": "...", "translation": "..."}, ...] 以及 {"strings": {...}}。

注意：
  * 多行对话在导出时会合并成一条（用 \\n 分隔），导入时再拆回多行 401 指令。
  * 请保留 \\C[1]、\\N[1]、\\V[1]、%1 这类控制符，工具会对比并给出警告。
  * 只处理 data/*.json 中的标准文本字段；插件参数、图片文字不处理。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from copy import deepcopy
from pathlib import Path

VERSION = "0.1.0"

JAPANESE_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff66-\uff9f]")
CONTROL_ONLY_RE = re.compile(r"^(?:\s|\\[A-Za-z]+\[[^\]]*])+$")
NUMERIC_RE = re.compile(r"^[\s\d\W_]+$", re.UNICODE)
PLACEHOLDER_RE = re.compile(r"\\[A-Za-z]+\[[^\]]*]|%[0-9]+")

# data/*.json 中按字段名直接取文本的表
DB_FIELDS: dict[str, tuple[str, ...]] = {
    "Actors.json": ("name", "nickname", "profile"),
    "Classes.json": ("name",),
    "Skills.json": ("name", "description", "message1", "message2"),
    "Items.json": ("name", "description"),
    "Weapons.json": ("name", "description"),
    "Armors.json": ("name", "description"),
    "Enemies.json": ("name",),
    "States.json": ("name", "message1", "message2", "message3", "message4"),
}

TEXT_COMMAND = 401      # Show Text 的文本行
SCROLL_COMMAND = 405    # Show Scrolling Text 的文本行


# --------------------------------------------------------------------------
# 基础判断
# --------------------------------------------------------------------------
def is_translatable(value: object) -> bool:
    """是否值得送去翻译：非空、不是纯数字/符号、不是纯控制符、含日文字符。"""
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False
    if NUMERIC_RE.match(text):
        return False
    if CONTROL_ONLY_RE.match(text):
        return False
    return bool(JAPANESE_RE.search(text))


# --------------------------------------------------------------------------
# 定位游戏
# --------------------------------------------------------------------------
def resolve_game(path_str: str) -> tuple[Path, Path, Path]:
    """返回 (game_dir, app_dir, data_dir)。

    game_dir : 含 Game.exe 的那层（用于放备份）
    app_dir  : 含 js/ 与 data/ 的那层（可能是 root 或 root/www）
    data_dir : app_dir/data
    """
    p = Path(path_str).expanduser().resolve()
    if not p.exists():
        raise SystemExit(f"[x] 路径不存在: {p}")

    # 直接传了 data 目录
    if p.is_dir() and p.name.lower() == "data" and (p / "System.json").exists():
        app = p.parent
        game = app.parent if app.name.lower() == "www" else app
        return game, app, p

    candidates = [
        p,
        p / "www",
        p / "resources" / "app",
        p / "resources" / "app" / "www",
    ]
    for base in candidates:
        d = base / "data"
        if d.is_dir() and (d / "System.json").exists():
            game = base.parent if base.name.lower() == "www" else base
            return game, base, d

    # 退一步：向下找 2 层
    for hit in sorted(p.glob("*/data/System.json")) + sorted(p.glob("*/*/data/System.json")):
        d = hit.parent
        app = d.parent
        game = app.parent if app.name.lower() == "www" else app
        return game, app, d

    raise SystemExit(
        "[x] 没找到 data/System.json。\n"
        "    请把参数指向游戏根目录（含 Game.exe）或其中的 www 目录。"
    )


def detect_engine(app_dir: Path) -> str:
    js = app_dir / "js"
    if (js / "rmmz_core.js").exists():
        return "RPG Maker MZ"
    if (js / "rpg_core.js").exists():
        return "RPG Maker MV"
    return "RPG Maker MV/MZ (未确认)"


# --------------------------------------------------------------------------
# 读写 JSON（保持原紧凑/缩进风格）
# --------------------------------------------------------------------------
def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def detect_indent(text: str) -> int | None:
    for line in text.splitlines()[1:30]:
        m = re.match(r"^( +)\S", line)
        if m:
            return len(m.group(1))
    return None


def dump_json_like(data: object, original: str) -> str:
    """尽量保持原文件风格：单行紧凑 vs. 缩进。"""
    line_count = original.count("\n") + 1
    avg_line = len(original) / line_count
    indent = detect_indent(original) if (line_count > 3 and avg_line < 500) else None
    if indent:
        return json.dumps(data, ensure_ascii=False, indent=indent) + "\n"
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def write_json(path: Path, data: object, original: str) -> None:
    text = dump_json_like(data, original)
    tmp = path.with_name(path.name + ".rpgm_textport_mv_mz.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# 文本收集 / 替换
# --------------------------------------------------------------------------
class Handler:
    def __init__(self, mode: str, translations: dict[str, str] | None = None) -> None:
        self.mode = mode
        self.translations = translations or {}
        self.order: list[str] = []
        self.seen: set[str] = set()
        self.context: dict[str, list[str]] = {}
        self.occurrences = 0
        self.hits = 0
        self.misses = 0
        self.placeholder_mismatch: list[tuple[str, str]] = []

    # -- export ------------------------------------------------------------
    def _record(self, text: str, where: str) -> None:
        self.occurrences += 1
        if text in self.seen:
            lst = self.context[text]
            if len(lst) < 3 and where not in lst:
                lst.append(where)
            return
        self.seen.add(text)
        self.order.append(text)
        self.context[text] = [where]

    # -- import ------------------------------------------------------------
    def _lookup(self, text: str) -> str | None:
        got = self.translations.get(text)
        if got is None:
            got = self.translations.get(text.strip())
        return got

    def _check_placeholders(self, src: str, dst: str) -> None:
        if sorted(PLACEHOLDER_RE.findall(src)) != sorted(PLACEHOLDER_RE.findall(dst)):
            if len(self.placeholder_mismatch) < 20:
                self.placeholder_mismatch.append((src, dst))

    # -- 统一入口 ----------------------------------------------------------
    def visit(self, value: object, where: str) -> str | None:
        """export 模式只记录；import 模式返回译文或 None（表示不改）。"""
        if not is_translatable(value):
            return None
        assert isinstance(value, str)
        if self.mode == "export":
            self._record(value, where)
            return None

        new = self._lookup(value)
        if new is None:
            self.misses += 1
            return None
        self.hits += 1
        self._check_placeholders(value, new)
        return new


def apply_value(container: dict, key: str, handler: Handler, where: str) -> bool:
    old = container.get(key)
    new = handler.visit(old, f"{where}.{key}")
    if new is not None and new != old:
        container[key] = new
        return True
    return False


def apply_index(container: list, index: int, handler: Handler, where: str) -> bool:
    if not (0 <= index < len(container)):
        return False
    old = container[index]
    new = handler.visit(old, f"{where}[{index}]")
    if new is not None and new != old:
        container[index] = new
        return True
    return False


# --------------------------------------------------------------------------
# 事件指令
# --------------------------------------------------------------------------
def reflow_lines(cmds: list, start: int, end: int, new_lines: list[str], code: int) -> None:
    """把 [start, end) 的文本行替换成 new_lines，必要时增删指令。"""
    if not new_lines:
        new_lines = [""]
    existing = end - start

    for k in range(min(existing, len(new_lines))):
        params = cmds[start + k].get("parameters")
        if isinstance(params, list):
            if params:
                params[0] = new_lines[k]
            else:
                params.append(new_lines[k])
        else:
            cmds[start + k]["parameters"] = [new_lines[k]]

    if len(new_lines) < existing:
        del cmds[start + len(new_lines):end]
    elif len(new_lines) > existing:
        template = cmds[end - 1]
        extra = []
        for line in new_lines[existing:]:
            new_cmd = deepcopy(template)
            new_cmd["code"] = code
            params = new_cmd.get("parameters")
            if isinstance(params, list) and params:
                params[0] = line
            else:
                new_cmd["parameters"] = [line]
            extra.append(new_cmd)
        cmds[start + existing:start + existing] = extra


def process_commands(cmds: object, handler: Handler, where: str) -> bool:
    if not isinstance(cmds, list):
        return False
    changed = False
    i = 0
    while i < len(cmds):
        cmd = cmds[i]
        if not isinstance(cmd, dict):
            i += 1
            continue
        code = cmd.get("code")
        params = cmd.get("parameters")
        if not isinstance(params, list):
            params = []

        # Show Text (101) / Show Scrolling Text (105)：把连续文本行合并成一段
        if code in (101, 105):
            if code == 101 and len(params) >= 5:
                # MZ: parameters[4] 是说话人名字
                changed |= apply_index(params, 4, handler, f"{where}:speaker")
            text_code = TEXT_COMMAND if code == 101 else SCROLL_COMMAND
            j = i + 1
            while j < len(cmds) and isinstance(cmds[j], dict) and cmds[j].get("code") == text_code:
                j += 1
            if j > i + 1:
                lines: list[str] = []
                for k in range(i + 1, j):
                    p = cmds[k].get("parameters")
                    if isinstance(p, list) and p and isinstance(p[0], str):
                        lines.append(p[0])
                    else:
                        lines.append("")
                block = "\n".join(lines)
                new_block = handler.visit(block, f"{where}:msg")
                if new_block is not None and new_block != block:
                    new_lines = new_block.split("\n")
                    reflow_lines(cmds, i + 1, j, new_lines, text_code)
                    changed = True
                    i = i + 1 + len(new_lines)
                    continue
            i = j
            continue

        # Show Choices
        if code == 102 and params and isinstance(params[0], list):
            for idx in range(len(params[0])):
                changed |= apply_index(params[0], idx, handler, f"{where}:choice")
        # 402 = When [xxx]，保持编辑器显示一致
        elif code == 402 and len(params) >= 2 and isinstance(params[1], str):
            changed |= apply_index(params, 1, handler, f"{where}:when")
        # 320/324/325 = 更改名字/昵称/简介
        elif code in (320, 324, 325) and len(params) >= 2:
            changed |= apply_index(params, 1, handler, f"{where}:name")

        i += 1
    return changed


# --------------------------------------------------------------------------
# 各文件类型
# --------------------------------------------------------------------------
def process_system(data: dict, handler: Handler, rel: str) -> bool:
    changed = False
    for key in ("gameTitle", "currencyUnit"):
        if isinstance(data.get(key), str):
            changed |= apply_value(data, key, handler, rel)

    terms = data.get("terms")
    if isinstance(terms, dict):
        for key in ("basic", "commands", "params"):
            arr = terms.get(key)
            if isinstance(arr, list):
                for i in range(len(arr)):
                    changed |= apply_index(arr, i, handler, f"{rel}.terms.{key}")
        msgs = terms.get("messages")
        if isinstance(msgs, dict):
            for key in list(msgs.keys()):
                if isinstance(msgs.get(key), str):
                    changed |= apply_value(msgs, key, handler, f"{rel}.terms.messages")

    for key in ("armorTypes", "elements", "equipTypes", "skillTypes", "weaponTypes"):
        arr = data.get(key)
        if isinstance(arr, list):
            for i in range(len(arr)):
                changed |= apply_index(arr, i, handler, f"{rel}.{key}")
    return changed


def process_map(data: dict, handler: Handler, rel: str) -> bool:
    changed = False
    if isinstance(data.get("displayName"), str):
        changed |= apply_value(data, "displayName", handler, rel)
    events = data.get("events")
    if isinstance(events, list):
        for ei, event in enumerate(events):
            if not isinstance(event, dict):
                continue
            pages = event.get("pages")
            if not isinstance(pages, list):
                continue
            for pi, page in enumerate(pages):
                if isinstance(page, dict):
                    changed |= process_commands(page.get("list"), handler, f"{rel} ev{ei} p{pi}")
    return changed


def process_troops(data: list, handler: Handler, rel: str) -> bool:
    changed = False
    for ti, troop in enumerate(data):
        if not isinstance(troop, dict):
            continue
        pages = troop.get("pages")
        if not isinstance(pages, list):
            continue
        for pi, page in enumerate(pages):
            if isinstance(page, dict):
                changed |= process_commands(page.get("list"), handler, f"{rel} tr{ti} p{pi}")
    return changed


def process_common_events(data: list, handler: Handler, rel: str) -> bool:
    changed = False
    for ei, event in enumerate(data):
        if isinstance(event, dict):
            changed |= process_commands(event.get("list"), handler, f"{rel} ce{ei}")
    return changed


def process_map_infos(data: list, handler: Handler, rel: str) -> bool:
    changed = False
    for i, info in enumerate(data):
        if isinstance(info, dict) and isinstance(info.get("name"), str):
            changed |= apply_value(info, "name", handler, f"{rel}[{i}]")
    return changed


def process_database(data: list, fields: tuple[str, ...], handler: Handler, rel: str) -> bool:
    changed = False
    for i, row in enumerate(data):
        if not isinstance(row, dict):
            continue
        for field in fields:
            if isinstance(row.get(field), str):
                changed |= apply_value(row, field, handler, f"{rel}[{i}]")
    return changed


def iter_data_files(data_dir: Path) -> list[Path]:
    return sorted(
        p for p in data_dir.glob("*.json")
        if p.is_file()
    )


def dispatch(path: Path, data: object, handler: Handler, rel: str) -> bool:
    name = path.name
    if name == "System.json" and isinstance(data, dict):
        return process_system(data, handler, rel)
    if name == "MapInfos.json" and isinstance(data, list):
        return process_map_infos(data, handler, rel)
    if name == "CommonEvents.json" and isinstance(data, list):
        return process_common_events(data, handler, rel)
    if name == "Troops.json" and isinstance(data, list):
        return process_troops(data, handler, rel)
    if name.startswith("Map") and name.endswith(".json") and isinstance(data, dict):
        return process_map(data, handler, rel)
    if name in DB_FIELDS and isinstance(data, list):
        return process_database(data, DB_FIELDS[name], handler, rel)
    return False


# --------------------------------------------------------------------------
# export
# --------------------------------------------------------------------------
def write_export(out: Path, keys: list[str], split: int) -> list[Path]:
    def dump(chunk: list[str]) -> str:
        return json.dumps({k: "" for k in chunk}, ensure_ascii=False, indent=2) + "\n"

    if split <= 0 or len(keys) <= split:
        out.write_text(dump(keys), encoding="utf-8")
        return [out]

    total = (len(keys) + split - 1) // split
    width = max(3, len(str(total)))
    stem, suffix = out.stem, (out.suffix or ".json")
    for stale in out.parent.glob(f"{stem}.part*{suffix}"):
        stale.unlink()  # 清掉上次分片留下的旧文件
    written: list[Path] = []
    for i in range(total):
        part = out.with_name(f"{stem}.part{i + 1:0{width}d}{suffix}")
        part.write_text(dump(keys[i * split:(i + 1) * split]), encoding="utf-8")
        written.append(part)
    return written


def cmd_export(args: argparse.Namespace) -> int:
    game_dir, app_dir, data_dir = resolve_game(args.game)
    engine = detect_engine(app_dir)
    handler = Handler("export")

    files = iter_data_files(data_dir)
    skipped: list[str] = []
    for path in files:
        try:
            original = read_text(path)
            data = json.loads(original)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            skipped.append(f"{path.name}: {exc}")
            continue
        dispatch(path, data, handler, path.name)

    out = Path(args.output).expanduser()
    if not out.is_absolute():
        out = Path.cwd() / out
    out.parent.mkdir(parents=True, exist_ok=True)

    written = write_export(out, handler.order, args.split)

    print(f"引擎      : {engine}")
    print(f"游戏目录  : {game_dir}")
    print(f"data 目录 : {data_dir}")
    print(f"扫描文件  : {len(files) - len(skipped)} 个" + (f"（跳过 {len(skipped)} 个）" if skipped else ""))
    print(f"唯一文本  : {len(handler.order)} 条")
    print(f"出现次数  : {handler.occurrences} 次")
    if len(written) == 1:
        print(f"导出文件  : {written[0]}")
    else:
        print(f"导出文件  : {len(written)} 个分片（每片 {args.split} 条）")
        for p in written:
            print(f"  - {p}")
    if skipped:
        print("跳过的文件（可能不是标准 JSON）:")
        for line in skipped[:10]:
            print(f"  - {line}")
    if not handler.order:
        print("[!] 没有提取到任何文本。可能是游戏使用了自定义加密/打包。")
        return 1
    return 0


# --------------------------------------------------------------------------
# import
# --------------------------------------------------------------------------
def load_translations(path: Path) -> dict[str, str]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"[x] 无法读取翻译文件 {path}: {exc}")

    pairs: dict[str, str] = {}
    if isinstance(raw, dict) and isinstance(raw.get("strings"), dict):
        raw = raw["strings"]

    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(k, str) and isinstance(v, str):
                pairs[k] = v
    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            src = item.get("text") or item.get("原文") or item.get("source")
            dst = item.get("translation") or item.get("译文") or item.get("target") or item.get("zh")
            if isinstance(src, str) and isinstance(dst, str):
                pairs[src] = dst
    else:
        raise SystemExit("[x] 翻译文件格式不认识：应为 {原文: 译文} 或 [{text, translation}]")

    cleaned: dict[str, str] = {}
    for src, dst in pairs.items():
        dst = dst.replace("\r\n", "\n").replace("\r", "\n")
        if dst.strip() and dst.strip() != src.strip():
            cleaned[src] = dst
    return cleaned


def load_translation_path(path: Path) -> dict[str, str]:
    """支持单个文件，或一个目录（合并目录下所有 *.json，便于分片翻译）。"""
    if not path.is_dir():
        return load_translations(path)

    merged: dict[str, str] = {}
    conflicts = 0
    parts = sorted(path.glob("*.json"))
    if not parts:
        raise SystemExit(f"[x] 目录里没有 *.json: {path}")
    for part in parts:
        for src, dst in load_translations(part).items():
            if src in merged and merged[src] != dst:
                conflicts += 1
            merged[src] = dst
    if conflicts:
        print(f"[!] 分片之间有 {conflicts} 条同一原文的译文不一致，已以后读到的为准。")
    return merged


def cmd_import(args: argparse.Namespace) -> int:
    game_dir, app_dir, data_dir = resolve_game(args.game)
    engine = detect_engine(app_dir)
    translations = load_translation_path(Path(args.translation))
    if not translations:
        raise SystemExit("[x] 翻译文件里没有有效译文（值为空或与原文相同）。")

    handler = Handler("import", translations)
    files = iter_data_files(data_dir)
    changed_files: list[tuple[Path, object, str, int]] = []
    skipped: list[str] = []

    for path in files:
        before_hits = handler.hits
        try:
            original = read_text(path)
            data = json.loads(original)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            skipped.append(f"{path.name}: {exc}")
            continue
        changed = dispatch(path, data, handler, path.name)
        if changed:
            changed_files.append((path, data, original, handler.hits - before_hits))

    print(f"引擎      : {engine}")
    print(f"data 目录 : {data_dir}")
    print(f"译文条数  : {len(translations)}")
    print(f"替换次数  : {handler.hits}")
    print(f"未命中    : {handler.misses} 次")
    print(f"待写文件  : {len(changed_files)} 个")

    if handler.placeholder_mismatch:
        print(f"\n[!] 有 {len(handler.placeholder_mismatch)} 处控制符（\\C[1]、%1 等）与原文不一致，例如：")
        for src, dst in handler.placeholder_mismatch[:5]:
            print(f"    原文: {src[:60]}")
            print(f"    译文: {dst[:60]}")

    if skipped:
        print("\n跳过的文件（可能不是标准 JSON）:")
        for line in skipped[:10]:
            print(f"  - {line}")

    if not changed_files:
        print("\n没有需要写入的内容。")
        return 0

    if args.dry_run:
        print("\n[dry-run] 未写入任何文件。")
        for path, _data, _orig, n in changed_files[:20]:
            print(f"  - {path.name}: {n} 处")
        return 0

    backup_dir = None
    if not args.no_backup:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup_dir = game_dir / "_rpgm_textport_mv_mz_backup" / stamp
        for path, _data, _original, _n in changed_files:
            dst = backup_dir / path.relative_to(game_dir)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dst)  # 字节级备份，避免换行/编码差异
    else:
        print("\n[!] --no-backup：没有备份，请自行承担风险。")

    for path, data, original, _n in changed_files:
        write_json(path, data, original)

    if backup_dir is not None:
        manifest = {
            "createdAt": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tool": f"rpgm-textport-mv-mz {VERSION}",
            "gameDir": str(game_dir),
            "files": [
                {"path": str(p.relative_to(game_dir)), "replacements": n}
                for p, _d, _o, n in changed_files
            ],
            "totalReplacements": handler.hits,
        }
        (backup_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"\n备份目录  : {backup_dir}")

    print("完成。启动游戏即可看到译文（建议先备份存档）。")
    return 0


# --------------------------------------------------------------------------
# info
# --------------------------------------------------------------------------
def cmd_info(args: argparse.Namespace) -> int:
    game_dir, app_dir, data_dir = resolve_game(args.game)
    print(f"引擎      : {detect_engine(app_dir)}")
    print(f"游戏目录  : {game_dir}")
    print(f"程序目录  : {app_dir}")
    print(f"data 目录 : {data_dir}")
    print(f"数据文件  : {len(iter_data_files(data_dir))} 个")
    plugins = app_dir / "js" / "plugins"
    if plugins.is_dir():
        print(f"插件数量  : {len(list(plugins.glob('*.js')))} 个（插件参数不在本工具处理范围）")
    return 0


# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rpgm_textport_mv_mz.py",
        description="RPG Maker MV/MZ 文本导出/导入",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python rpgm_textport_mv_mz.py export \"D:\\Games\\Foo\" -o foo.json\n"
            "  python rpgm_textport_mv_mz.py import \"D:\\Games\\Foo\" foo.json --dry-run\n"
            "  python rpgm_textport_mv_mz.py import \"D:\\Games\\Foo\" foo.json\n"
        ),
    )
    parser.add_argument("--version", action="version", version=f"rpgm-textport-mv-mz {VERSION}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_info = sub.add_parser("info", help="查看游戏信息")
    p_info.add_argument("game", help="游戏根目录（含 Game.exe）或其中的 www 目录")
    p_info.set_defaults(func=cmd_info)

    p_export = sub.add_parser("export", help="导出待翻译文本")
    p_export.add_argument("game", help="游戏根目录或其中的 www 目录")
    p_export.add_argument("-o", "--output", default="rpgm_textport_mv_mz_strings.json", help="输出文件（默认 rpgm_textport_mv_mz_strings.json）")
    p_export.add_argument("--split", type=int, default=0, metavar="N", help="可选：按每片 N 条拆成多个文件，便于分批翻译")
    p_export.set_defaults(func=cmd_export)

    p_import = sub.add_parser("import", help="导入译文并写回游戏")
    p_import.add_argument("game", help="游戏根目录或其中的 www 目录")
    p_import.add_argument("translation", help="翻译好的 JSON 文件，或包含多个分片的目录")
    p_import.add_argument("--dry-run", action="store_true", help="只统计，不写入")
    p_import.add_argument("--no-backup", action="store_true", help="不备份（不推荐）")
    p_import.set_defaults(func=cmd_import)
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        print("\n已取消。")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
