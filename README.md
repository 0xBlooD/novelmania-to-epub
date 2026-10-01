---
title: Novel Mania to EPUB
emoji: 📚
colorFrom: indigo
colorTo: purple
sdk: gradio
app_file: app.py
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

### 2. Gerar EPUBs via Linha de Comando (CLI)
Basta rodar o script passando o **slug** ou a **URL completa** da obra no Novel Mania:

```bash
python generate_novel.py <slug>
```

#### Exemplos:
```bash
# Para Hyouka (https://novelmania.com.br/novels/hyouka)
python generate_novel.py hyouka

# Para Amor Invisível Sob o Céu Noturno
python generate_novel.py amor-invisivel-sob-o-ceu-noturno

# Para 5 Centímetros por Segundo
python generate_novel.py 5-centimetros-por-segundo
```

> **Atalho:** Você também pode rodar `python build_epubs.py`, que por padrão gera os volumes de Hyouka.

### 3. Rodar a Interface Web (Gradio) Localmente
Para usar uma interface gráfica amigável no navegador com pré-visualização e download direto em `.zip`:

```bash
python app.py
```
Acesse no seu navegador: `http://localhost:7860`.

---

## ☁️ Deploy Gratuito no Hugging Face Spaces

O repositório está configurado para o SDK **Gradio** do Hugging Face Spaces:

1. Crie um novo Space no Hugging Face: [huggingface.co/new-space](https://huggingface.co/new-space).
2. Configure:
   - **Space SDK:** `Gradio`
   - **Template:** `Blank`
   - **Space Hardware:** `CPU basic (100% gratuito)`
3. Conecte com o seu repositório GitHub ou envie os arquivos via Git para o Space:
   ```bash
   git remote add space https://huggingface.co/spaces/<seu-usuario>/<nome-do-space>
   git push space main
   ```
4. O Hugging Face iniciará o app automaticamente na URL pública do seu Space!

---

## 📁 Estrutura de Pastas Gerada (Localmente)

Quando você executa o script na sua máquina, os arquivos são organizados localmente na pasta `epub_<slug>`:

```text
epub_<slug>/
├── .cache_chapters/    # Cache dos HTMLs brutos e dados dos capítulos
├── .cache_covers/      # Capas em alta resolução otimizadas para e-readers
├── .cache_images/      # Ilustrações internas dos capítulos baixadas localmente
├── novel/              # Arquivos .epub gerados prontos para leitura
└── <slug>_epubs.zip    # Arquivo ZIP consolidado (criado via Web UI)
```

> 🔒 **Importante sobre o Git / GitHub:**  
> O arquivo `.gitignore` deste repositório está configurado com `epub_*` e `*.epub`. Portanto, **nenhuma pasta de novel gerada, arquivo de cache ou EPUB é enviado para o GitHub**, mantendo o repositório 100% limpo, leve e focado apenas no código-fonte.

---

## 🔍 Como Conseguimos Coletar as Informações do Novel Mania

O [Novel Mania](https://novelmania.com.br) é uma aplicação moderna construída sobre TanStack Start/Router. A extração dos dados foi desenhada através da análise da sua infraestrutura:

### 1. Metadados Gerais da Obra (API REST)
* **Endpoint:** `GET https://novelmania.com.br/api/novels/{slug}`
* **Dados obtidos:** Título oficial, autor original, sinopse completa, status da obra, categorias/gêneros e as URLs da capa original em alta definição (`cover.original` / `cover.large`).

### 2. Catálogo e Agrupamento de Volumes (API REST Paginada)
* **Endpoint:** `GET https://novelmania.com.br/api/novels/{slug}/chapters?page={N}&limit=50`
* **Dados obtidos:** A lista completa de capítulos na ordem correta, slugs de leitura, créditos da equipe (`translators` e `editors`), e o objeto `unity`:
  * O campo `unity.name` indica a qual volume o capítulo pertence (ex: *Volume 1*, *Volume 2* ou *Volume Único*). Isso permite ao gerador agrupar com precisão os capítulos em seus respectivos livros.

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

## 📖 Exemplo de Obra Testada: Hyouka

Ao executar `python generate_novel.py hyouka`, os 48 capítulos traduzidos de **Hyouka: Série Clube de Literatura Clássica** (Honobu Yonezawa / tradução por slag) são compilados localmente na pasta `epub_hyouka/novel/`:

| Arquivo Gerado Localmente | Volume | Subtítulo Original | Capítulos |
| :--- | :--- | :--- | :---: |
| `Hyouka - Volume 1.epub` | Volume 1 | *The niece of time* | 9 capítulos |
| `Hyouka - Volume 2 - O Fim de Jogo do Tolo.epub` | Volume 2 | *Why didn't she ask Eba?* | 7 capítulos (com mapa ilustrado) |
| `Hyouka - Volume 3 - A Ordem de Kudryavka.epub` | Volume 3 | *Welcome to Kanya Festa!* | 13 capítulos |
| `Hyouka - Volume 4 - A Boneca que Faz Desvio.epub` | Volume 4 | *Little birds can remember* | 7 capítulos |
| `Hyouka - Volume 5 - A Estimativa da Distancia entre Dois.epub` | Volume 5 | *It walks by past* | 7 capítulos (inclui Epílogo) |
| `Hyouka - Volume 6 - Mesmo Que Me Digam Que Agora Tenho Asas.epub` | Volume 6 | *Even Though I'm Told Now That I Have Wings* | 5 capítulos |
