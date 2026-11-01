"""Rebuild the small synthetic, two-page PDF used by policy tests.

Run with Python from any directory. This uses only the standard library and
does not include material from the store's supplied policy document.
"""

from pathlib import Path


def build_pdf() -> bytes:
    page_lines = [
        ["Synthetic store policies", "Horário de atendimento: segunda a sexta, das 10h às 17h."],
        ["Synthetic return policy", "Devolução: fale com a equipe para solicitar análise.",
         "A promoção não muda este procedimento de atendimento."],
    ]
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>"]
    for index, lines in enumerate(page_lines):
        content_id = 4 + index * 2
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 7 0 R >> >> /Contents {content_id} 0 R >>".encode("ascii")
        )
        commands = [b"BT /F1 12 Tf 50 740 Td"]
        for line_number, line in enumerate(lines):
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            if line_number:
                commands.append(b"0 -24 Td")
            commands.append(b"(" + escaped.encode("cp1252") + b") Tj")
        commands.append(b"ET")
        stream = b"\n".join(commands)
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    result = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f"{number} 0 obj\n".encode("ascii") + body + b"\nendobj\n")
    xref_offset = len(result)
    result.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    result.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(result)


if __name__ == "__main__":
    Path(__file__).with_name("policies.pdf").write_bytes(build_pdf())
