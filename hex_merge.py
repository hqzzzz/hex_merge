#!/usr/bin/env python3
"""
多 Intel HEX / 纯 BIN  合并成单一连续 BIN 工具
用法：
    # 只传 HEX（原用法不变）
    python hex_merge.py  -o fw.bin  [-b 0x08000000]  [-p 0xFF]  *.hex

    # 混合 HEX + BIN
    python hex_merge.py  -o fw.bin  -b 0x08000000  app.hex  boot.bin@0x08000000  cfg.bin@0x0800FC00
    其中 boot.bin@0x08000000  表示把 boot.bin 加载到 0x08000000
"""
import argparse
import pathlib
import struct
import sys
from typing import List, Tuple, Iterable

# ---------- HEX 解析 ----------
def read_hex_records(path: pathlib.Path) -> Iterable[Tuple[int, bytes]]:
    ext_addr = 0
    with path.open('r', encoding='ascii', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line[0] != ':': continue
            count = int(line[1:3], 16)
            addr  = int(line[3:7], 16)
            rtype = int(line[7:9], 16)
            data  = bytes.fromhex(line[9:9+count*2])
            if rtype == 0x00:          # Data
                yield ext_addr + addr, data
            elif rtype == 0x04:        # Extended Linear Address
                ext_addr = struct.unpack('>H', data)[0] << 16
            elif rtype == 0x01:        # EOF
                break

# ---------- BIN 解析 ----------
def read_bin(path: pathlib.Path, load_addr: int) -> Iterable[Tuple[int, bytes]]:
    """把整个 BIN 当成一段连续数据返回"""
    yield load_addr, path.read_bytes()

# ---------- 统一收集 ----------
def collect_segments(file_list: List[str]) -> List[Tuple[int, int, bytes]]:
    """
    输入: 混合路径串，可能带 @addr 后缀
          例如  ['boot.hex', 'app.bin@0x08004000']
    输出: 已合并/排序的 [(start, end, data), ...]
    """
    segs = []
    for item in file_list:
        # 拆分 @addr
        if '@' in item:
            path_str, addr_str = item.rsplit('@', 1)
            load_addr = int(addr_str, 0)
            p = pathlib.Path(path_str)
        else:
            p = pathlib.Path(item)
            load_addr = None          # 仅 BIN 需要 addr

        if not p.exists():
            print(f'跳过不存在文件: {p}', file=sys.stderr)
            continue

        # 按扩展名分流
        if p.suffix.lower() == '.hex':
            for addr, data in read_hex_records(p):
                segs.append((addr, addr + len(data), data))
        elif p.suffix.lower() == '.bin':
            if load_addr is None:
                print(f'错误：BIN 文件必须显式给出加载地址  {p}@<addr>', file=sys.stderr)
                sys.exit(1)
            for addr, data in read_bin(p, load_addr):
                segs.append((addr, addr + len(data), data))
        else:
            print(f'跳过未知类型文件: {p}', file=sys.stderr)

    # 按起始地址排序
    segs.sort(key=lambda x: x[0])
    # 合并重叠/相邻
    merged = []
    for st, ed, data in segs:
        if not merged:
            merged.append((st, ed, data))
            continue
        lst, led, ldata = merged[-1]
        if st <= led:  # 重叠或相邻
            new_ed = max(ed, led)
            if st < lst:  # 向前伸展
                merged[-1] = (st, new_ed, data[:lst-st] + ldata)
            elif ed > led:  # 向后伸展
                merged[-1] = (lst, new_ed, ldata + data[led-st:])
        else:
            merged.append((st, ed, data))
    return merged


# ---------- 写 BIN ----------
def write_bin(segments: List[Tuple[int, int, bytes]],
              out_path: pathlib.Path,
              base_addr: int = 0,
              pad: int = 0xFF) -> None:
    if not segments:
        print('警告：没有任何数据段，输出空文件', file=sys.stderr)
        out_path.write_bytes(b'')
        return
    first = segments[0][0]
    last  = segments[-1][1]
    start = min(first, base_addr)
    end   = last
    total = end - start
    print(f'BIN 范围 0x{start:X} .. 0x{end:X}  (size = {total} bytes)')
    with out_path.open('wb') as f:
        pos = start
        for st, ed, data in segments:
            if st > pos:
                f.write(bytes([pad]) * (st - pos))
                pos = st
            f.write(data)
            pos = ed
        if pos < end:
            f.write(bytes([pad]) * (end - pos))
    print(f'已生成 {out_path}  ({out_path.stat().st_size} bytes)')


# ---------- 命令行 ----------
def main():
    parser = argparse.ArgumentParser(description='合并多个 HEX/BIN 为单一连续 BIN')
    parser.add_argument('inputs', nargs='+', help='HEX/BIN 路径，BIN 文件可用 @addr 指定加载地址')
    parser.add_argument('-o', '--output', required=True, help='输出 BIN 文件名')
    parser.add_argument('-b', '--base', type=lambda x: int(x, 0), default=0x08000000,
                        help='输出 BIN 的基地址（前面补 pad）')
    parser.add_argument('-p', '--pad', type=lambda x: int(x, 0), default=0xFF,
                        help='填充字节，默认 0xFF')
    args = parser.parse_args()

    segments = collect_segments(args.inputs)
    write_bin(segments, pathlib.Path(args.output), args.base, args.pad)


if __name__ == '__main__':
    main()