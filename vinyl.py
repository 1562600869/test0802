#!/usr/bin/env python3
import argparse
import json
import os
import sys
from datetime import datetime

DATA_FILE = os.path.expanduser("~/.vinyl.json")
VALID_CONDITIONS = ["全新", "近全新", "良好", "一般", "差"]


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"records": [], "next_id": 1}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_record(args):
    if args.condition not in VALID_CONDITIONS:
        print(f"错误：品相必须是以下之一：{', '.join(VALID_CONDITIONS)}")
        sys.exit(1)

    if args.price <= 0:
        print("错误：价格必须是正整数")
        sys.exit(1)

    data = load_data()
    record = {
        "id": data["next_id"],
        "title": args.title,
        "artist": args.artist,
        "year": args.year,
        "genre": args.genre,
        "condition": args.condition,
        "price": args.price,
        "sold": False,
        "sold_price": None,
        "sold_date": None,
        "created_at": datetime.now().isoformat()
    }
    data["records"].append(record)
    data["next_id"] += 1
    save_data(data)
    print(f"已添加：{record['artist']} - {record['title']} (ID: {record['id']})")


def list_records(args):
    data = load_data()
    records = data["records"]

    if args.genre:
        records = [r for r in records if r["genre"] == args.genre and not r["sold"]]
    else:
        records = [r for r in records if not r["sold"]]

    if args.artist:
        records = [r for r in records if r["artist"] == args.artist]

    if not records:
        print("没有找到唱片")
        return

    print(f"{'ID':<4} {'专辑名':<20} {'艺术家':<15} {'年份':<6} {'流派':<10} {'品相':<8} {'价格':<8}")
    print("-" * 75)
    for r in records:
        print(f"{r['id']:<4} {r['title']:<20} {r['artist']:<15} {r['year']:<6} {r['genre']:<10} {r['condition']:<8} ¥{r['price']:<7}")


def show_stats(args):
    data = load_data()
    records = data["records"]
    unsold = [r for r in records if not r["sold"]]
    sold = [r for r in records if r["sold"]]

    print("=" * 50)
    print("黑胶唱片收藏统计")
    print("=" * 50)
    print(f"总张数：{len(records)} (在售：{len(unsold)}，已售：{len(sold)})")

    total_value = sum(r["price"] for r in unsold)
    total_sold_value = sum(r["sold_price"] for r in sold)
    print(f"总价值（在售）：¥{total_value}")
    print(f"已售总额：¥{total_sold_value}")
    print(f"累计总价值：¥{total_value + total_sold_value}")

    print("\n最贵的5张唱片：")
    sorted_by_price = sorted(records, key=lambda x: x["sold_price"] if x["sold"] else x["price"], reverse=True)[:5]
    for i, r in enumerate(sorted_by_price, 1):
        price = r["sold_price"] if r["sold"] else r["price"]
        status = "已售" if r["sold"] else "在售"
        print(f"  {i}. {r['artist']} - {r['title']}: ¥{price} ({status})")

    print("\n流派分布：")
    genre_count = {}
    for r in records:
        genre = r["genre"]
        genre_count[genre] = genre_count.get(genre, 0) + 1
    for genre, count in sorted(genre_count.items(), key=lambda x: x[1], reverse=True):
        print(f"  {genre}: {count} 张")


def search_records(args):
    data = load_data()
    keyword = args.keyword.lower()
    results = [
        r for r in data["records"]
        if keyword in r["title"].lower() or keyword in r["artist"].lower()
    ]

    if not results:
        print(f"没有找到包含 '{args.keyword}' 的唱片")
        return

    print(f"找到 {len(results)} 张唱片：")
    print(f"{'ID':<4} {'专辑名':<20} {'艺术家':<15} {'年份':<6} {'流派':<10} {'状态':<8}")
    print("-" * 70)
    for r in results:
        status = "已售" if r["sold"] else "在售"
        print(f"{r['id']:<4} {r['title']:<20} {r['artist']:<15} {r['year']:<6} {r['genre']:<10} {status:<8}")


def sell_record(args):
    data = load_data()
    record = next((r for r in data["records"] if r["id"] == args.id), None)

    if not record:
        print(f"错误：找不到 ID 为 {args.id} 的唱片")
        sys.exit(1)

    if record["sold"]:
        print(f"错误：该唱片已于 {record['sold_date']} 出售，不可重复操作")
        sys.exit(1)

    if args.price <= 0:
        print("错误：出售价格必须是正整数")
        sys.exit(1)

    record["sold"] = True
    record["sold_price"] = args.price
    record["sold_date"] = datetime.now().strftime("%Y-%m-%d")
    save_data(data)
    print(f"已标记出售：{record['artist']} - {record['title']}")
    print(f"出售价格：¥{args.price}，日期：{record['sold_date']}")


def main():
    parser = argparse.ArgumentParser(description="黑胶唱片收藏管理工具")
    subparsers = parser.add_subparsers(dest="command", help="命令")

    add_parser = subparsers.add_parser("add", help="添加唱片")
    add_parser.add_argument("title", help="专辑名称")
    add_parser.add_argument("--artist", required=True, help="艺术家")
    add_parser.add_argument("--year", type=int, required=True, help="发行年份")
    add_parser.add_argument("--genre", required=True, help="流派")
    add_parser.add_argument("--condition", required=True, choices=VALID_CONDITIONS, help=f"品相：{', '.join(VALID_CONDITIONS)}")
    add_parser.add_argument("--price", type=int, required=True, help="价格")

    list_parser = subparsers.add_parser("list", help="列出唱片")
    list_parser.add_argument("--genre", help="按流派过滤")
    list_parser.add_argument("--artist", help="按艺术家过滤")

    subparsers.add_parser("stats", help="显示统计信息")

    search_parser = subparsers.add_parser("search", help="搜索唱片")
    search_parser.add_argument("keyword", help="搜索关键词")

    sell_parser = subparsers.add_parser("sell", help="标记出售")
    sell_parser.add_argument("id", type=int, help="唱片ID")
    sell_parser.add_argument("--price", type=int, required=True, help="出售价格")

    args = parser.parse_args()

    if args.command == "add":
        add_record(args)
    elif args.command == "list":
        list_records(args)
    elif args.command == "stats":
        show_stats(args)
    elif args.command == "search":
        search_records(args)
    elif args.command == "sell":
        sell_record(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
