import sys, json, re, collections
ext = json.load(open(sys.argv[1], encoding="utf-8")); res = json.load(open(sys.argv[2], encoding="utf-8"))
pal = lambda s: re.findall(r"[\wÀ-ÿ]+", s or "")
fonte = collections.Counter(w for p in ext["paginas"] for l in p["linhas"] for w in pal(l["t"]))
alvo = collections.Counter(w for a in res["artigos"] for w in pal(a["texto"])) + collections.Counter(pal(res["ementa"])) + collections.Counter(pal(res["preambulo"]))
falta = fonte - alvo; sobra = alvo - fonte
print("palavras vigentes no PDF:", sum(fonte.values()), "| nos artigos+ementa+preâmbulo:", sum(alvo.values()))
print("faltam (top):", falta.most_common(40)); print("sobram:", sobra.most_common(10))
