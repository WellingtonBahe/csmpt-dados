"""Estrutura o Temário Unificado do MPT (Res. CSMPT 195/2022, compilada) a partir do texto extraído (extrair.py).
Uso: python3 -I temario.py extraido.json saida.json
Saída: itens [{codigo, nivel, nome, area, pai, especificacao_obrigatoria, tema_complementar_obrigatorio,
                notas, fundamentacao, o_que_cadastrar, pagina}] + cabeçalho da resolução.
"""
import sys, json, re

CAB = re.compile(r"^(MINISTÉRIO PÚBLICO DO TRABALHO$|PROCURADORIA[- ]GERAL DO TRABALHO$|CONSELHO SUPERIOR$|RESOLUÇÃO N[ºo°] ?\d+, DE|\((Publicada|Republicada|Alterada|Retificada) (no|pela|pelas|em) |\d+$)")
COD = re.compile(r"^(\d+(?:\.\d+)+)\.?\s+(.+)$")
SECOES = {"NOTAS EXPLICATIVAS": "notas", "FUNDAMENTAÇÃO NORMATIVA": "fundamentacao", "FUNDAMENTOS NORMATIVOS": "fundamentacao", "O QUE CADASTRAR": "o_que_cadastrar"}
NIVEIS = {1: "area", 2: "grupo", 3: "tema", 4: "subtema"}


def limpa(s):
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\(\s+", "(", s)
    s = re.sub(r"\s+\)", ")", s)
    return s


def flags(nome):
    n = nome.lower()
    return {"especificacao_obrigatoria": "especificação obrigatória" in n,
            "tema_complementar_obrigatorio": "código do tema complementar" in n or "codigo do tema complementar" in n}


def sem_obs(nome):
    return limpa(re.sub(r"\((campo de especifica|incluir obrigatoriamente)[^)]*\)", "", nome, flags=re.I))


def main(entrada, saida):
    d = json.load(open(entrada, encoding="utf-8"))
    pags = []
    cab = []
    for p in d["paginas"]:
        ls = []
        for l in p["linhas"]:
            t = l["t"]
            if not t or re.fullmatch(r"[()\s]*", t):
                continue
            if CAB.match(t):
                if p["n"] == 1:
                    cab.append(t)
                continue
            ls.append(t)
        pags.append((p["n"], ls))

    # 1) lista de códigos (do "A N E X O" até a primeira página de notas)
    itens, ordem = {}, []
    inicio_notas = None
    area_atual, esperando_nome_area = None, False
    em_lista = False
    for n, ls in pags:
        if any(x in SECOES for x in ls):
            inicio_notas = n
            break
        for t in ls:
            if t.replace(" ", "") == "ANEXO":
                em_lista = True
                continue
            if not em_lista or t.startswith("(Redação dada"):
                continue
            ma = re.match(r"^ÁREA TEMÁTICA (\d+)(?!\.)(?:\s+(.*))?$", t)
            if ma:
                area_atual = ma.group(1)
                itens[area_atual] = {"codigo": area_atual, "nivel": "area", "nome": ma.group(2) or "", "pagina": n}
                ordem.append(area_atual)
                esperando_nome_area = True
                continue
            mc = COD.match(t)
            if mc:
                cod = mc.group(1)
                itens[cod] = {"codigo": cod, "nivel": NIVEIS.get(cod.count(".") + 1, "subtema"), "nome": mc.group(2), "pagina": n}
                ordem.append(cod)
                esperando_nome_area = False
                continue
            if ordem:  # continuação do nome anterior
                ult = itens[ordem[-1]]
                ult["nome"] = (ult["nome"] + " " + t).strip()
    for c in ordem:
        it = itens[c]
        it["nome_completo"] = limpa(it["nome"])
        it.update(flags(it["nome_completo"]))
        it["nome"] = sem_obs(it["nome_completo"])
        partes = c.split(".")
        it["area"] = partes[0]
        it["pai"] = ".".join(partes[:-1]) if len(partes) > 1 else None

    # 2) notas explicativas, fundamentação e o que cadastrar, por código
    blocos = []
    atual = None
    cabecalho = None  # linhas do cabeçalho em montagem
    secao = None
    for n, ls in pags:
        if inicio_notas is None or n < inicio_notas:
            continue
        for t in ls:
            if re.match(r"^ÁREA TEMÁTICA \d+", t):
                # cabeçalho de bloco ou folha de rosto da área: a folha de rosto é descartada quando outro cabeçalho começa
                cabecalho = [t]
                atual, secao = None, None
                continue
            if t in SECOES:
                if cabecalho is not None:
                    h = limpa(" ".join(cabecalho))
                    cods = re.findall(r"(?:GRUPO TEMÁTICO|TEMA|SUBTEMA)\s+(\d+(?:\.\d+)+)", h)
                    ca = re.match(r"^ÁREA TEMÁTICA (\d+)", h)
                    cod = cods[-1].rstrip(".") if cods else (ca.group(1) if ca else None)
                    atual = {"codigo": cod, "cabecalho": h, "pagina": n, "notas": [], "fundamentacao": [], "o_que_cadastrar": []}
                    blocos.append(atual)
                    cabecalho = None
                secao = SECOES[t]
                continue
            if cabecalho is not None:
                cabecalho.append(t)
                continue
            if atual is not None and secao:
                atual[secao].append(t)
    sem_codigo, repetidos = [], []
    for b in blocos:
        c = b["codigo"]
        if c not in itens:
            sem_codigo.append(b["cabecalho"])
            continue
        it = itens[c]
        if "pagina_notas" in it:
            repetidos.append(c)
            continue
        it["pagina_notas"] = b["pagina"]
        it["notas"] = limpa(" ".join(b["notas"])) or None
        # fundamentação: uma referência por linha (como no PDF), juntando as quebradas
        f = []
        for x in b["fundamentacao"]:
            if f and (x[:1].islower() or re.match(r"^[\d(,;]", x) or f[-1].endswith((",", " e", " de", " do", " da", "-"))):
                f[-1] += " " + x
            else:
                f.append(x)
        it["fundamentacao"] = [limpa(x) for x in f] or None
        it["o_que_cadastrar"] = limpa(" ".join(b["o_que_cadastrar"])) or None
    ident = " ".join(cab)
    alteracoes = [{"resolucao": int(m.group(1)), "data": m.group(2)} for m in re.finditer(r"Alterada pela Resolu[çc][ãa]o n[ºo°]\s*(\d+),?\s*de\s*([\d/]+)", ident)]
    publicacao = [re.sub(r"^\(|\)$", "", c) for c in cab if re.match(r"^\((Publicada|Republicada)", c)]
    out = {"numero": 195, "publicacao": publicacao, "alteracoes": alteracoes, "sha256": d["sha256"], "paginas": d["paginas_total"],
           "itens": [itens[c] for c in ordem], "blocos_sem_codigo_na_lista": sem_codigo, "codigos_com_mais_de_um_bloco": repetidos}
    json.dump(out, open(saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
