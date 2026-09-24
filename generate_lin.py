#!/usr/bin/env python3
"""Fetch a bridge result page, generate validated BBO LIN files, and retry failures."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

SUITS = "SHDC"
RANKS = "23456789TJQKA"
DECK = {suit + rank for suit in SUITS for rank in RANKS}
DEALER_NUMBERS = {"North": "1", "East": "2", "South": "3", "West": "4"}
VULNERABILITY = {"None": "o", "N-S": "n", "E-W": "e", "Both": "b"}
HAND_LINE = re.compile(r"^\s*([SHDC]):(.*)$")


def fetch_page(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "euc-jp"
    return raw.decode(charset, errors="replace")


def clean_cards(value: str) -> str:
    return value.replace("10", "T").replace(" ", "").strip()


def block_from_lines(lines: list[str], start: int) -> str | None:
    values: dict[str, str] = {}
    for offset in range(4):
        match = HAND_LINE.match(lines[start + offset])
        if not match or match.group(1) in values:
            return None
        values[match.group(1)] = clean_cards(match.group(2))
    if set(values) != set(SUITS):
        return None
    return "".join(suit + values[suit] for suit in SUITS)


def parse_board(chunk: str) -> dict[str, object] | None:
    board_match = re.search(r"Board:\s*(\d+)", chunk)
    dealer_match = re.search(r"Dealer:\s*(North|East|South|West)", chunk)
    vul_match = re.search(r"Vul:\s*([^\n]+)", chunk)
    if not (board_match and dealer_match and vul_match):
        return None

    lines = chunk.splitlines()
    north_start = None
    for index in range(len(lines) - 3):
        if "*NN*" in lines[index]:
            continue
        if re.match(r"^\s*S:", lines[index]) and block_from_lines(lines, index):
            north_start = index
            break
    if north_start is None:
        return None

    south_start = None
    for index in range(len(lines) - 4, north_start, -1):
        if block_from_lines(lines, index):
            south_start = index
            break
    if south_start is None:
        return None

    inline = {}
    patterns = {
        "S": re.compile(r"S:(.*?)\*NN\* S:(.*)$"),
        "H": re.compile(r"H:(.*?)\s+W\s+E H:(.*)$"),
        "D": re.compile(r"D:(.*?)\s+W\s+E D:(.*)$"),
        "C": re.compile(r"C:(.*?)\*SS\* C:(.*)$"),
    }
    for line in lines[north_start + 4 : south_start]:
        for suit, pattern in patterns.items():
            match = pattern.search(line)
            if match:
                inline[suit] = (clean_cards(match.group(1)), clean_cards(match.group(2)))
                break
    if set(inline) != set(SUITS):
        return None

    north = block_from_lines(lines, north_start)
    south = block_from_lines(lines, south_start)
    west = "".join(suit + inline[suit][0] for suit in SUITS)
    east = "".join(suit + inline[suit][1] for suit in SUITS)
    return {
        "board": int(board_match.group(1)),
        "dealer": dealer_match.group(1),
        "vulnerability": vul_match.group(1).strip(),
        "hands": [south, west, north, east],
    }


def parse_page(text: str) -> dict[int, dict[str, object]]:
    boards = {}
    for chunk in text.split("---------------------------------"):
        board = parse_board(chunk)
        if board:
            boards[board["board"]] = board
    return boards


def validate_board(board: dict[str, object]) -> list[str]:
    hands = board["hands"]
    cards = [
        suit + rank
        for hand in hands
        for suit, ranks in re.findall(r"([SHDC])([2-9TJQKA]*)", hand)
        for rank in ranks
    ]
    deal = ",".join(hands)
    reasons = []
    if len(hands) != 4:
        reasons.append(f"4手ではなく{len(hands)}手です")
    if len(cards) != 52:
        reasons.append(f"カードが52枚ではなく{len(cards)}枚です")
    duplicates = sorted(card for card, count in Counter(cards).items() if count > 1)
    missing = sorted(DECK - set(cards))
    if duplicates:
        reasons.append("重複カード: " + ", ".join(duplicates))
    if missing:
        reasons.append("不足カード: " + ", ".join(missing))
    invalid = sorted(set(re.sub(r"[SHDC2-9TJQKA,]", "", deal)))
    if invalid:
        reasons.append("不正な表記: " + ", ".join(invalid))
    return reasons


def lin_text(board: dict[str, object]) -> str:
    vulnerability = VULNERABILITY[board["vulnerability"]]
    number = board["board"]
    dealer = str((number + 1) % 4 + 1)
    hands = ",".join(board["hands"])
    return f"pn|South,West,North,East|st||md|{dealer}{hands}|sv|{vulnerability}|rh||ah|Board {number}|\n"


def append_error(path: Path, board_number: int, reasons: list[str]) -> None:
    with path.open("a", encoding="utf-8") as error_file:
        error_file.write(f"- #{board_number}.lin: " + "; ".join(reasons) + "\n")


def create_link_file(path: Path, board_numbers: set[int]) -> None:
    if path.exists():
        return
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", path.parent.name)
    if match:
        date = f"{int(match.group(2))}/{int(match.group(3))}"
    else:
        date = path.parent.name
    period = ""
    if "Session 1" in path.parent.name:
        period = " 午前"
    elif "Session 2" in path.parent.name:
        period = " 午後"
    lines = [f"{date}{period}"]
    lines.extend(f"{number}番: " for number in sorted(board_numbers))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args()
    if args.attempts < 1 or args.attempts > 3:
        parser.error("--attempts must be between 1 and 3")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pending = set()
    last_reasons: dict[int, list[str]] = {}
    generated = 0
    for attempt in range(1, args.attempts + 1):
        try:
            boards = parse_page(fetch_page(args.url))
        except Exception as error:
            print(f"取得失敗 (試行{attempt}): {error}", file=sys.stderr)
            continue
        create_link_file(args.output_dir / "link.txt", set(boards))
        if not pending:
            pending = set(boards)
        for board_number in sorted(pending - set(boards)):
            last_reasons[board_number] = ["ページからハンドを取得できませんでした"]
        for board_number in sorted(pending & set(boards)):
            reasons = validate_board(boards[board_number])
            if not reasons:
                (args.output_dir / f"#{board_number}.lin").write_text(
                    lin_text(boards[board_number]), encoding="utf-8"
                )
                pending.remove(board_number)
                generated += 1
            else:
                last_reasons[board_number] = reasons
        if not pending:
            break

    if pending:
        error_path = args.output_dir / "error.txt"
        if not error_path.exists():
            error_path.write_text("# LIN変換エラー\n\n", encoding="utf-8")
        for board_number in sorted(pending):
            append_error(error_path, board_number, last_reasons[board_number])
        print(f"保留: {len(pending)}件。{error_path} を確認してください。")
    print(f"生成: {generated}件")
    return 1 if pending else 0


if __name__ == "__main__":
    raise SystemExit(main())
