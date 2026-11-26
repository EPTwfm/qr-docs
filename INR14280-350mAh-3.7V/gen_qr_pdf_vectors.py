#!/usr/bin/env python3
"""
生成与原参考 PDF (qr-2003-sc2500mahx10-12v.pdf) 完全相同格式的二维码 PDF。
格式规格：
  - PDF 1.3, 页面 25x25mm = 70.86614 x 70.86614 pt
  - 矢量矩形绘制 re f*（非位图），纯黑白
  - 纠错级别 H (30%)，qrcode 库自动选版本
  - 静区 4 模块，ASCII85 + Flate 压缩内容流
用法: python gen_qr_pdf_vectors.py <URL> <输出.pdf>
"""
import sys, re, base64, zlib, qrcode

PAGE = 70.86614          # 25mm in points
BORDER = 4               # 静区模块数
EC = qrcode.constants.ERROR_CORRECT_H

def make_pdf(url, out):
    qr = qrcode.QRCode(error_correction=EC, border=BORDER)
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()          # bool 二维数组，True=黑
    n = len(matrix)                   # 含 border 的总模块数
    unit = PAGE / n                   # 每模块尺寸 (pt)

    # 构造内容流：白底 + 黑块（合并水平连续黑块，与原 PDF 一致）
    parts = [
        "1 0 0 1 0 0 cm  BT /F1 12 Tf 14.4 TL ET\n",
        "1 1 1 rg\n",
        f"n 0 0 {PAGE:.5f} {PAGE:.5f} re f*\n",
        "0 0 0 rg\n",
    ]
    for r, row in enumerate(matrix):
        c = 0
        while c < n:
            if row[c]:
                c0 = c
                while c < n and row[c]:
                    c += 1
                x = c0 * unit
                y = PAGE - (r + 1) * unit   # 从顶部绘制
                w = (c - c0) * unit
                parts.append(f"n {x:.6f} {y:.6f} {w:.6f} {unit:.6f} re f*\n")
            else:
                c += 1
    content = "".join(parts).encode("latin-1")

    # ASCII85 + Flate 压缩（与原 PDF 相同的过滤链）
    compressed = zlib.compress(content)
    a85 = base64.a85encode(compressed) + b"~>"

    objs = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE} {PAGE}] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>".encode())
    objs.append(b"<< /Length " + str(len(a85)).encode() + b" /Filter [ /ASCII85Decode /FlateDecode ] >>\nstream\n" + a85 + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out_data = bytearray(b"%PDF-1.3\n")
    offsets = [0]
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out_data))
        out_data += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out_data)
    out_data += f"xref\n0 {len(objs)+1}\n".encode()
    out_data += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out_data += f"{off:010d} 00000 n \n".encode()
    out_data += f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()

    with open(out, "wb") as f:
        f.write(out_data)
    print(f"生成: {out}")
    print(f"  URL: {url}")
    print(f"  版本 {qr.version}, {n}x{n} 模块, 每模块 {unit:.6f}pt, 黑块 {sum(sum(r) for r in matrix)}")
    print(f"  文件大小 {len(out_data)} bytes")

if __name__ == "__main__":
    make_pdf(sys.argv[1], sys.argv[2])
