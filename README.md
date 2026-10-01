---
title: Novel Mania to EPUB
emoji: 📚
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Novel Mania EPUB Generator

Gerador automatizado de arquivos **EPUB** em padrão de alta qualidade para obras traduzidas disponibilizadas no site [Novel Mania](https://novelmania.com.br).

O script organiza automaticamente os capítulos por volume, baixa as capas oficiais e ilustrações internas, limpa a formatação do texto e compila arquivos `.epub` prontos para leitura em qualquer leitor digital (**Kindle, Kobo, Apple Books, Calibre, Moon+ Reader, etc.**).

---

## 🚀 Como Usar

### 1. Preparar o Ambiente
Recomenda-se utilizar o ambiente virtual Python (`.venv`):

```bash
# Cria o ambiente virtual (caso ainda não exista)
python3 -m venv .venv

# Ativa o ambiente virtual
source .venv/bin/activate

# Instala as dependências
pip install -r requirements.txt
```

### 2. Gerar EPUBs de Qualquer Obra
Basta rodar o script passando o **slug** da obra (a parte final da URL da novel no site):

```bash
python generate_novel.py <slug>
```

#### Exemplos:
```bash
# Para Hyouka (https://novelmania.com.br/novels/hyouka)
python generate_novel.py hyouka

# Para 5 Centímetros por Segundo (https://novelmania.com.br/novels/5-centimetros-por-segundo)
python generate_novel.py 5-centimetros-por-segundo
```

> **Atalho:** Você também pode rodar `python build_epubs.py`, que por padrão gera os volumes de Hyouka.

### 3. Rodar a Interface Web / API Localmente
Você também pode iniciar o servidor web com interface gráfica:

```bash
uvicorn app:app --port 7860 --reload
```
Acesse no seu navegador: `http://localhost:7860`.

#### Endpoints da API:
- `GET /api/info?slug={slug}`: Retorna metadados, contagem de capítulos e prévia da capa.
- `GET /api/download?slug={slug}`: Gera os EPUBs da obra e faz o streaming direto do arquivo `.zip`.

---

## ☁️ Deploy no Hugging Face Spaces

O repositório já está 100% configurado para rodar no **Hugging Face Spaces** com **Docker**:

1. Crie um novo Space no Hugging Face: [huggingface.co/new-space](https://huggingface.co/new-space).
2. Defina:
   - **Space SDK:** `Docker` (Blank)
   - **Hardware:** `CPU basic (gratuito - 16 GB RAM)`
   - **Visibility:** `Public` ou `Private`
3. Conecte com o seu repositório GitHub ou envie os arquivos via Git para o remote do Space:
   ```bash
   git remote add space https://huggingface.co/spaces/<seu-usuario>/<nome-do-space>
   git push space main
   ```
4. O Hugging Face construirá o contêiner automaticamente e fornecerá uma URL pública gratuita!

---

## 📁 Estrutura de Pastas Gerada

Para manter o repositório limpo ao versionar no Git/GitHub, o gerador cria uma pasta com prefixo `epub_<slug>`:

```text
epub_hyouka/
├── .cache_chapters/    # Cache dos HTMLs brutos e dados parseados dos capítulos
├── .cache_covers/      # Capas em alta resolução otimizadas para e-readers
├── .cache_images/      # Ilustrações internas dos capítulos baixadas localmente
└── novel/              # Arquivos .epub finais gerados
    ├── Hyouka - Volume 1.epub
    ├── Hyouka - Volume 2 - O Fim de Jogo do Tolo.epub
    ├── Hyouka - Volume 3 - A Ordem de Kudryavka.epub
    ├── Hyouka - Volume 4 - A Boneca que Faz Desvio.epub
    ├── Hyouka - Volume 5 - A Estimativa da Distancia entre Dois.epub
    └── Hyouka - Volume 6 - Mesmo Que Me Digam Que Agora Tenho Asas.epub
```

> **Git & GitHub:** O arquivo `.gitignore` já está configurado com `epub_*` para garantir que nem os arquivos pesados de cache nem os arquivos `.epub` gerados sejam enviados acidentalmente para o repositório.

O sistema de cache evita requisições redundantes ao site: se você rodar o comando novamente para uma obra já baixada, a compilação leva apenas alguns segundos.

---

## 🔍 Como Conseguimos Coletar as Informações do Novel Mania

O [Novel Mania](https://novelmania.com.br) é uma aplicação moderna construída sobre TanStack Start/Router. A extração dos dados foi desenhada através da análise da sua infraestrutura:

### 1. Metadados Gerais da Obra (API REST)
* **Endpoint:** `GET https://novelmania.com.br/api/novels/{slug}`
* **Dados obtidos:** Título oficial, autor original, sinopse completa, status da obra, categorias/gêneros e as URLs da capa original em alta definição (`cover.original` / `cover.large`).

### 2. Catálogo e Agrupamento de Volumes (API REST Paginada)
* **Endpoint:** `GET https://novelmania.com.br/api/novels/{slug}/chapters?page={N}&limit=50`
* **Dados obtidos:** A lista completa de capítulos na ordem correta, slugs de leitura, créditos da equipe (`translators` e `editors`), e o objeto `unity`:
  * O campo `unity.name` indica a qual volume o capítulo pertence (ex: *Volume 1*, *Volume 2* ou *Volume Único*). Isso permite ao gerador agrupar com precisão matemática os capítulos em seus respectivos livros.

### 3. Conteúdo Completo dos Capítulos (Páginas SSR)
* Embora o endpoint direto de texto via API exija autenticação (403), as páginas web públicas de leitura (`https://novelmania.com.br/novels/{slug}/capitulos/{chapter_slug}`) entregam o HTML completo já pré-renderizado no servidor (SSR).
* O script extrai a área de leitura identificada pela classe CSS `rich-text-content prose`:
  * **Diálogos:** Mantém os travessões (`—`) e pontuações originais.
  * **Pensamentos/Cartas:** Preserva a formatação em itálico (`<em>`).
  * **Drop-caps:** Mantém as iniciais destacadas (`<strong>C</strong>OSTUMA-SE...`).
  * **Divisores de Cena:** Detecta marcações como `***` ou `* * *` e converte em ornamentos tipográficos limpos (`❖ ❖ ❖`).

### 4. Extração e Incorporação de Ilustrações
* Qualquer imagem encontrada no corpo dos capítulos (`<img src="...">`, como mapas, diagramas e ilustrações da light novel) é baixada e otimizada (redimensionada para largura máxima de 1600px em JPEG com alta qualidade).
* No arquivo EPUB, a referência remota é substituída por uma referência local interna (`OEBPS/images/...`), garantindo que o livro funcione **100% offline** em qualquer dispositivo.

### 5. Construção e Validação do Padrão EPUB 3 / EPUB 2
Os arquivos são empacotados seguindo rigidamente os padrões do IDPF / W3C:
* **Mimetype sem compressão:** O arquivo `mimetype` com valor `application/epub+zip` é gravado no início do arquivo ZIP no modo `STORED` (não comprimido), como exige a especificação.
* **Entidades XML válidas:** Entidades HTML nomeadas (como `&nbsp;`, `&mdash;`, `&eacute;`) são convertidas para caracteres UTF-8 puros com `html.unescape()`, impedindo erros de XML nos leitores mais rigorosos.
* **Sumário Duplo:** Contém `OEBPS/nav.xhtml` (para leitores modernos EPUB 3) e `OEBPS/toc.ncx` (para leitores legados e leitores Kindle).
* **Tipografia e Estilo:** Arquivo `styles.css` embutido com tipografia serifada, recuo tradicional de parágrafos, quebras suaves e suporte automático a **Modo Noturno (Dark Mode)** e Séphia.

---

## 📖 Obra Atual no Repositório: Hyouka

Os 48 capítulos traduzidos de **Hyouka: Série Clube de Literatura Clássica** (por Honobu Yonezawa, traduzido por slag) já estão compilados e validados na pasta [epub_hyouka/novel/](epub_hyouka/novel/):

| Arquivo EPUB | Volume | Subtítulo Original | Capítulos |
| :--- | :--- | :--- | :---: |
| [`Hyouka - Volume 1.epub`](epub_hyouka/novel/Hyouka%20-%20Volume%201.epub) | Volume 1 | *The niece of time* | 9 capítulos |
| [`Hyouka - Volume 2 - O Fim de Jogo do Tolo.epub`](epub_hyouka/novel/Hyouka%20-%20Volume%202%20-%20O%20Fim%20de%20Jogo%20do%20Tolo.epub) | Volume 2 | *Why didn't she ask Eba?* | 7 capítulos (com mapa ilustrado) |
| [`Hyouka - Volume 3 - A Ordem de Kudryavka.epub`](epub_hyouka/novel/Hyouka%20-%20Volume%203%20-%20A%20Ordem%20de%20Kudryavka.epub) | Volume 3 | *Welcome to Kanya Festa!* | 13 capítulos |
| [`Hyouka - Volume 4 - A Boneca que Faz Desvio.epub`](epub_hyouka/novel/Hyouka%20-%20Volume%204%20-%20A%20Boneca%20que%20Faz%20Desvio.epub) | Volume 4 | *Little birds can remember* | 7 capítulos |
| [`Hyouka - Volume 5 - A Estimativa da Distancia entre Dois.epub`](epub_hyouka/novel/Hyouka%20-%20Volume%205%20-%20A%20Estimativa%20da%20Distancia%20entre%20Dois.epub) | Volume 5 | *It walks by past* | 7 capítulos (inclui Epílogo) |
| [`Hyouka - Volume 6 - Mesmo Que Me Digam Que Agora Tenho Asas.epub`](epub_hyouka/novel/Hyouka%20-%20Volume%206%20-%20Mesmo%20Que%20Me%20Digam%20Que%20Agora%20Tenho%20Asas.epub) | Volume 6 | *Even Though I'm Told Now That I Have Wings* | 5 capítulos |
