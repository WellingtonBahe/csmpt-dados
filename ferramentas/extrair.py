"""Extrai texto de PDF de resolução do CSMPT separando o que está riscado (redação revogada).
Uso: python3 -I extrair.py entrada.pdf saida.json
Saída: {paginas: [{n, linhas: [{t (vigente), r (riscado, se houver)}]}], sha256, paginas_total}
O traço de riscado vem como retângulo fino (altura < 2,5 pt) desenhado sobre o meio da linha.
"""
import sys, json, hashlib
import pymupdf

CABECALHO = ("MINISTÉRIO PÚBLICO DO TRABALHO", "PROCURADORIA GERAL DO TRABALHO", "CONSELHO SUPERIOR")


def tracos(pagina):
    out = []
    for d in pagina.get_drawings():
        for it in d["items"]:
            if it[0] == "re":
                r = it[1]
            elif it[0] == "l":
                p, q = it[1], it[2]
                if abs(p.y - q.y) > 1:
                    continue
                r = pymupdf.Rect(min(p.x, q.x), p.y - 0.5, max(p.x, q.x), p.y + 0.5)
            else:
                continue
            if r.height < 2.5 and r.width > 3:
                out.append(r)
    return out


def riscado(bbox, linhas_traco):
    x0, y0, x1, y1 = bbox
    cx = (x0 + x1) / 2
    h = y1 - y0
    for r in linhas_traco:
        ym = (r.y0 + r.y1) / 2
        # traço de riscado passa pelo terço central da altura do caractere (sublinhado fica embaixo)
        if r.x0 - 0.5 <= cx <= r.x1 + 0.5 and y0 + h * 0.3 <= ym <= y0 + h * 0.8:
            return True
    return False


def main(entrada, saida):
    dados = open(entrada, "rb").read()
    doc = pymupdf.open(stream=dados, filetype="pdf")
    paginas = []
    for i, pg in enumerate(doc):
        tr = tracos(pg)
        chars = []  # (y_base, x0, x1, c, riscado, tamanho)
        raw = pg.get_text("rawdict")
        for b in raw["blocks"]:
            for l in b.get("lines", []):
                for sp in l["spans"]:
                    for c in sp["chars"]:
                        chars.append((c["origin"][1], c["bbox"][0], c["bbox"][2], c["c"], bool(tr) and riscado(c["bbox"], tr), sp["size"]))
        tamanhos = sorted(z[5] for z in chars if z[3].strip())
        mediana = tamanhos[len(tamanhos) // 2] if tamanhos else 12
        normais = sorted((z for z in chars if z[5] >= 0.75 * mediana), key=lambda z: (z[0], z[1]))
        pequenos = [z for z in chars if z[5] < 0.75 * mediana]
        grupos = []
        for z in normais:
            if grupos and abs(grupos[-1][0] - z[0]) <= 1.5:
                grupos[-1][1].append(z)
            else:
                grupos.append([z[0], [z]])
        for z in pequenos:  # sobrescrito/subscrito: vai para a linha de base mais próxima (até 6 pt)
            perto = min(grupos, key=lambda g: abs(g[0] - z[0]), default=None)
            if perto is not None and abs(perto[0] - z[0]) <= 6:
                perto[1].append(z)
            else:
                grupos.append([z[0], [z]])
        grupos.sort(key=lambda g: g[0])
        linhas = []
        for _, cs in grupos:
            cs.sort(key=lambda z: z[1])
            vig, ris, ant = [], [], None
            for z in cs:
                if ant is not None and z[3] != " " and z[1] - ant[2] > 0.2 * z[5]:
                    (ris if z[4] else vig).append(" ")
                (ris if z[4] else vig).append(z[3])
                ant = z
            t = " ".join("".join(vig).split())
            r = " ".join("".join(ris).split())
            if t or r:
                linhas.append({"t": t, **({"r": r} if r else {})})
        paginas.append({"n": i + 1, "linhas": linhas})
    json.dump({"sha256": hashlib.sha256(dados).hexdigest(), "bytes": len(dados), "paginas_total": len(doc), "paginas": paginas},
              open(saida, "w", encoding="utf-8"), ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
