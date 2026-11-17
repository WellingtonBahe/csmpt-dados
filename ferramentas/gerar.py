"""Monta a pasta do repositório csmpt-dados a partir das saídas de resolucao.py e temario.py.
Uso: python3 -I gerar.py pasta_saida res1.json [res2.json ...] --temario 195.tem.json [--tabela tabela.json]
Cada arquivo fica com até ~100 KB (limite de CPU do Worker gratuito ao ler e gravar no D1).
"""
import sys, json, hashlib, os, datetime

LIMITE = 100_000
MAX_ITENS = 30  # o D1 aceita 50 consultas por chamada; cada item é uma gravação
PDF = "https://midia-ext.mpt.mp.br/pgt/csmpt/resolucoes/resolu{n}.pdf"


def grava(pasta, nome, obj, manifesto, **extra):
    txt = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    caminho = os.path.join(pasta, nome)
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    open(caminho, "w", encoding="utf-8").write(txt)
    b = txt.encode("utf-8")
    manifesto["arquivos"].append({"arquivo": nome, "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b), **extra})


def partes(itens, limite):
    atual, tam = [], 0
    for it in itens:
        n = len(json.dumps(it, ensure_ascii=False))
        if atual and (tam + n > limite or len(atual) >= MAX_ITENS):
            yield atual
            atual, tam = [], 0
        atual.append(it)
        tam += n
    if atual:
        yield atual


def main(argv):
    pasta = argv[0]
    args = argv[1:]
    temario = tabela = None
    if "--temario" in args:
        i = args.index("--temario"); temario = args[i + 1]; del args[i:i + 2]
    if "--tabela" in args:
        i = args.index("--tabela"); tabela = args[i + 1]; del args[i:i + 2]
    manifesto = {"gerado_em": datetime.date.today().isoformat(), "fonte": "PDFs compilados do CSMPT em https://mpt.mp.br/pgt/conselho-superior/resolucoes-1",
                 "arquivos": [], "pdfs": []}
    for f in args:
        r = json.load(open(f, encoding="utf-8"))
        n = r["numero"]
        pdf = {"numero": n, "url": PDF.format(n=n), "sha256": r["sha256"], "paginas": r["paginas"], "bytes": r.get("bytes_pdf")}
        manifesto["pdfs"].append(pdf)
        ficha = {k: r[k] for k in ("numero", "data", "ementa", "preambulo", "publicacao", "alteracoes")}
        ficha["pdf"] = pdf
        arts = r["artigos"]
        ps = list(partes(arts, LIMITE))
        for k, p in enumerate(ps):
            grava(pasta, f"resolucoes/{n}-{k + 1:02d}.json", {"ficha": ficha if k == 0 else None, "parte": k + 1, "partes": len(ps), "artigos": p},
                  manifesto, tipo="resolucao", numero=n, parte=k + 1, partes=len(ps))
    if temario:
        t = json.load(open(temario, encoding="utf-8"))
        ps = list(partes(t["itens"], LIMITE))
        for k, p in enumerate(ps):
            grava(pasta, f"temario/{t['numero']}-{k + 1:02d}.json", {"parte": k + 1, "partes": len(ps), "itens": p},
                  manifesto, tipo="temario", numero=t["numero"], parte=k + 1, partes=len(ps))
    if tabela:
        tb = json.load(open(tabela, encoding="utf-8"))
        ps = list(partes(tb["linhas"], LIMITE))
        for k, p in enumerate(ps):
            grava(pasta, f"tabela/tabela-{k + 1:02d}.json", {"lida_em": tb["lida_em"], "parte": k + 1, "partes": len(ps), "linhas": p}, manifesto, tipo="tabela", parte=k + 1, partes=len(ps))
    json.dump(manifesto, open(os.path.join(pasta, "manifesto.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"arquivos": [(a["arquivo"], a["bytes"]) for a in manifesto["arquivos"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
