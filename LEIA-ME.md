# csmpt-dados

Texto das resoluções do Conselho Superior do Ministério Público do Trabalho (CSMPT), extraído dos PDFs compilados que o MPT publica em https://mpt.mp.br/pgt/conselho-superior/resolucoes-1, para uso do conector Precedentes (repositório privado precedentes-mcp). São textos oficiais públicos; a fonte de verdade continua sendo o PDF do MPT e o Diário Oficial.

## Conteúdo

`manifesto.json` lista cada arquivo com o SHA-256 e os PDFs de origem (endereço, SHA-256, páginas e bytes). `resolucoes/NNN-PP.json` traz a ficha da resolução (na parte 1) e os artigos, cada um com capítulo, seção, página do PDF, texto vigente, notas de redação e, à parte, o texto riscado no PDF. `temario/195-PP.json` traz os códigos do Temário Unificado (anexo da Res. 195/2022, compilado), com nome, flags de especificação e de tema complementar, notas explicativas, fundamentação normativa e "o que cadastrar". Cada arquivo tem no máximo 30 itens, porque o Worker grava um arquivo por chamada no D1 do plano gratuito.

## Como refazer

Com Python 3 e PyMuPDF (`pip install pymupdf`), a partir dos PDFs baixados do site do MPT:

```
python3 -I ferramentas/extrair.py resolu235.pdf 235.json
python3 -I ferramentas/resolucao.py 235.json 235.res.json
python3 -I ferramentas/conferir.py 235.json 235.res.json
python3 -I ferramentas/extrair.py resolu195.pdf 195.json
python3 -I ferramentas/resolucao.py 195.json 195.res.json
python3 -I ferramentas/temario.py 195.json 195.tem.json
python3 -I ferramentas/gerar.py . 235.res.json 195.res.json --temario 195.tem.json
```

O extrator separa o texto riscado (o MPT risca a redação substituída com um traço desenhado sobre a linha) caractere a caractere. O `conferir.py` confere por programa que toda palavra vigente do PDF está em algum artigo, na ementa ou no preâmbulo. Depois de gravar os arquivos novos aqui, o Worker os copia sozinho em até uma hora.
