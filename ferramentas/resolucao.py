"""Divide em artigos o texto extraído (extrair.py) de uma resolução do CSMPT.
Uso: python3 -I resolucao.py extraido.json saida.json
Guarda o texto vigente de cada artigo, as notas de redação e, à parte, o texto riscado (redações substituídas ou revogadas).
"""
import sys, json, re

CAB = re.compile(r"^(MINISTÉRIO PÚBLICO DO TRABALHO$|PROCURADORIA[- ]GERAL DO TRABALHO$|CONSELHO SUPERIOR$|RESOLUÇÃO N[ºo°] ?\d+, DE|\(?(Publicada|Republicada|Alterada|Retificada) (no|pela|pelas|em) |Página \d+ de \d+$|\d+$)")
ART = re.compile(r"^Art\.\s*(\d+)\s*[ºo°]?(?:\s*-\s*([A-Z]))?\s*[.º°]?\s")
DISP = re.compile(r"^(Art\.\s*\d+|§\s*\d+|Parágrafo [úu]nico|[IVXLC]+\s*[–-]|[a-z]\)\s)")
DIVISAO = re.compile(r"^(CAPÍTULO|TÍTULO|Seção|SEÇÃO|Subseção|SUBSEÇÃO)\s+([IVXLC]+|[ÚU]NICA|[ÚU]nica)\b")
CARGO = re.compile(r"^(Presidente|Vice-President[ae]|Conselheir[oa]|Procurador)", re.I)
NOTA = re.compile(r"\((?:Redação dada|Revogad[oa]|Incluíd[oa]|Acrescentad[oa]|Acrescid[oa]|Inserid[oa]|Renumerad[oa]|Alterad[oa])[^()]*?(?:Resolução|Res\.)[^()]*\)\.?", re.I)


def limpa(s):
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([.,;:])", r"\1", s)
    s = re.sub(r"^[.,;:]\s*", "", s)
    s = re.sub(r"(§\s*\d+\s*[ºo°]?)\s*\.\s*\(", r"\1 (", s)
    return s


def rotulo_art(m):
    n = m.group(1)
    return n + ("-" + m.group(2) if m.group(2) else "")


def main(entrada, saida):
    d = json.load(open(entrada, encoding="utf-8"))
    linhas = []  # (pagina, vigente, riscado)
    cabecalho = []
    for p in d["paginas"]:
        for l in p["linhas"]:
            t, r = l["t"], l.get("r", "")
            if CAB.match(t) and not r:
                if p["n"] == 1:
                    cabecalho.append(t)
                continue
            # pedaço vigente que só sobrou de uma linha riscada (pontuação solta)
            if r and re.fullmatch(r"[\s.,;:()]*", t):
                t = ""
            linhas.append((p["n"], t, r))
    ident = " ".join(cabecalho)
    m = re.search(r"RESOLUÇÃO N[ºo°]\s*(\d+),?\s*DE\s+(\d{1,2})[º°]?\s+DE\s+([A-ZÇ]+)\s+(?:DE\s+)?(\d{4})", ident, re.I)
    MESES = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
    numero = int(m.group(1)) if m else None
    data = f"{int(m.group(2)):02d}/{MESES.index(m.group(3).upper()) + 1:02d}/{m.group(4)}" if m else None
    publicacao = [re.sub(r"^\(|\)$", "", c) for c in cabecalho if re.match(r"^\(?(Publicada|Republicada|Retificada)", c, re.I)]
    alteracoes = []
    for c in cabecalho:
        for x in re.finditer(r"Resolu[çc][ãa]o n[ºo°]\s*(\d+),?\s*de\s*([\d/.]+)", c, re.I):
            if re.match(r"^\(?Alterada", c, re.I):
                alteracoes.append({"resolucao": int(x.group(1)), "data": x.group(2).rstrip(".")})

    # ementa e preâmbulo: tudo antes do primeiro artigo ou da primeira divisão
    pre, i = [], 0
    while i < len(linhas) and not ART.match(linhas[i][1]) and not DIVISAO.match(linhas[i][1]):
        if linhas[i][1]:
            pre.append(linhas[i][1])
        i += 1
    txt_pre = " ".join(pre)
    k = txt_pre.find("O CONSELHO SUPERIOR")
    ementa = limpa(txt_pre[:k] if k > 0 else "")
    preambulo = limpa(txt_pre[k:] if k >= 0 else txt_pre)

    artigos, atual, riscado_alvo = [], None, None
    capitulo, secao, pendente_div = None, None, None
    por_rot = {}
    risc_por = {}

    def novo(rot, pagina):
        a = {"artigo": rot, "capitulo": capitulo, "secao": secao, "pagina": pagina, "vig": [], "risc": []}
        artigos.append(a)
        por_rot[rot] = a
        return a

    fim = False
    for j in range(i, len(linhas)):
        pg, t, r = linhas[j]
        if fim:
            break
        # assinaturas: nome em caixa alta seguido de cargo
        if t and not r and t == t.upper() and re.search(r"[A-ZÁÉÍÓÚ]{3}", t) and j + 1 < len(linhas) and CARGO.match(linhas[j + 1][1] or ""):
            fim = True
            break
        if r and re.fullmatch(r"(§\s*\d+\s*[ºo°]?|[IVXLC]+\s*[–-]|[a-z]\))", t or ""):
            r = t + " " + r  # rótulo vigente de dispositivo revogado: o riscado leva o rótulo junto
        if r:
            mr = ART.match(r + " ")
            if mr:
                riscado_alvo = rotulo_art(mr)
            chave = riscado_alvo or (atual["artigo"] if atual else None)
            if chave is not None:
                lst = risc_por.setdefault(chave, {"onde": atual["artigo"] if atual else None, "itens": []})["itens"]
                if DISP.match(r) or not lst:
                    lst.append(r)
                else:
                    lst[-1] += " " + r
        if not t:
            continue
        md = DIVISAO.match(t)
        if md:
            pendente_div = [md.group(1).upper(), t]
            continue
        if pendente_div and not ART.match(t + " "):
            # segunda linha da divisão é o nome
            nome = pendente_div[1] + " - " + t
            if pendente_div[0] in ("CAPÍTULO", "TÍTULO"):
                capitulo, secao = nome, None
            else:
                secao = nome
            pendente_div = None
            continue
        pendente_div = None
        ma = ART.match(t + " ")
        if ma:
            atual = novo(rotulo_art(ma), pg)
            riscado_alvo = None
            atual["vig"].append(t)
            continue
        if atual is None:
            continue
        if DISP.match(t):
            atual["vig"].append(t)
        else:
            atual["vig"][-1] += " " + t
        if riscado_alvo and not r:
            riscado_alvo = None

    for chave, v in risc_por.items():
        alvo = por_rot.get(chave) or por_rot.get(v["onde"])
        if alvo is not None:
            alvo["risc"].extend(v["itens"])
    saida_art = []
    for a in artigos:
        disp = [limpa(x) for x in a["vig"]]
        texto = "\n".join(x for x in disp if x)
        notas = []
        for x in NOTA.finditer(texto):
            n = re.sub(r"\)\.?$", ")", x.group(0))
            if n not in notas:
                notas.append(n)
        rot = a["artigo"]
        saida_art.append({"artigo": rot, "rotulo": f"Art. {rot}{'º' if rot.isdigit() and int(rot) < 10 else '.'}" if rot.isdigit() else f"Art. {rot}.",
                          "capitulo": a["capitulo"], "secao": a["secao"], "pagina": a["pagina"], "texto": texto,
                          "notas": notas, "texto_riscado": "\n".join(limpa(x) for x in a["risc"]) or None})
    out = {"numero": numero, "data": data, "ementa": ementa, "preambulo": preambulo, "publicacao": publicacao,
           "alteracoes": alteracoes, "sha256": d["sha256"], "bytes_pdf": d.get("bytes"), "paginas": d["paginas_total"], "artigos": saida_art}
    json.dump(out, open(saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
