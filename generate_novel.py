#!/usr/bin/env python3
"""
Gerador de EPUB para qualquer obra do Novel Mania (novelmania.com.br)
Uso:
    python generate_novel.py <slug>
Exemplo:
    python generate_novel.py hyouka
"""

import os
import sys
import re
import json
import html
import uuid
import time
import zipfile
import requests
from bs4 import BeautifulSoup
from PIL import Image
import io
import random

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://novelmania.com.br/',
}

CSS_STYLE = """
@charset "utf-8";

/* Estilo geral */
html, body {
    margin: 0;
    padding: 0;
    font-family: "Georgia", "Baskerville", "Palatino Linotype", "Times New Roman", serif;
    font-size: 1.05em;
    line-height: 1.7;
    color: #1a1a1a;
    background-color: #fafafa;
}

body {
    padding: 5% 7%;
}

/* Títulos */
h1.book-title {
    font-size: 2.1em;
    text-align: center;
    margin-top: 1.5em;
    margin-bottom: 0.2em;
    font-weight: 700;
    line-height: 1.25;
}

h2.book-subtitle {
    font-size: 1.3em;
    text-align: center;
    color: #4a4a4a;
    font-weight: normal;
    font-style: italic;
    margin-top: 0.2em;
    margin-bottom: 2em;
}

h1.chapter-title {
    font-size: 1.6em;
    text-align: center;
    margin-top: 1.2em;
    margin-bottom: 0.5em;
    font-weight: 700;
    line-height: 1.3;
}

.volume-tag {
    display: block;
    text-align: center;
    font-size: 0.85em;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #777777;
    margin-top: 1em;
    margin-bottom: 0.3em;
}

.staff-info {
    text-align: center;
    font-size: 0.85em;
    color: #666666;
    font-style: italic;
    margin-bottom: 2em;
    padding-bottom: 1em;
    border-bottom: 1px solid #e0e0e0;
}

/* Parágrafos e Diálogos */
p {
    margin-top: 0;
    margin-bottom: 0;
    text-indent: 1.5em;
    text-align: justify;
    hyphens: auto;
    -webkit-hyphens: auto;
}

p.first, p.no-indent {
    text-indent: 0;
}

p.blank-line {
    text-indent: 0;
    height: 1.2em;
    margin: 0;
}

.scene-break {
    text-align: center;
    margin: 1.8em 0;
    font-size: 1.2em;
    color: #888888;
}

/* Caixa de Metadados e Sinopse */
.meta-box {
    margin: 2em auto;
    max-width: 90%;
    padding: 1.2em 1.5em;
    border-top: 1px solid #ccc;
    border-bottom: 1px solid #ccc;
    font-size: 0.95em;
    line-height: 1.8;
}

.meta-row {
    margin: 0.3em 0;
}

.meta-label {
    font-weight: bold;
    color: #333333;
}

.synopsis-box {
    margin: 2em auto;
    padding: 1.2em 1.5em;
    background-color: rgba(0, 0, 0, 0.03);
    border-left: 4px solid #6b8299;
    border-radius: 4px;
    font-style: italic;
}

.synopsis-box p {
    text-indent: 0;
    margin-bottom: 0.8em;
}

.synopsis-box p:last-child {
    margin-bottom: 0;
}

/* Imagens e Ilustrações */
.illustration-wrap {
    text-align: center;
    margin: 2em auto;
}

.illustration-wrap img {
    max-width: 100%;
    height: auto;
    border-radius: 4px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.cover-wrapper {
    margin: 0;
    padding: 0;
    text-align: center;
    height: 100%;
}

.cover-wrapper img {
    max-width: 100%;
    max-height: 100%;
    height: auto;
}

/* Suporte a Modo Escuro */
@media (prefers-color-scheme: dark) {
    html, body {
        color: #e0e0e0;
        background-color: #1a1a1a;
    }
    h2.book-subtitle, .volume-tag, .staff-info {
        color: #a0a0a0;
    }
    .staff-info, .meta-box {
        border-color: #333333;
    }
    .synopsis-box {
        background-color: rgba(255, 255, 255, 0.05);
        border-left-color: #7b99b8;
    }
    .meta-label {
        color: #f0f0f0;
    }
}
"""

def clean_paragraph_html(p_raw: str, local_images_map: dict) -> str:
    """Limpa e formata o HTML do parágrafo, ajustando imagens e entidades."""
    if not p_raw or p_raw.strip() in ['&nbsp;', '']:
        return '<p class="blank-line">&#160;</p>'
    
    # Substitui URLs de imagem por referências locais
    for remote_url, local_rel in local_images_map.items():
        if remote_url in p_raw:
            return f'<div class="illustration-wrap"><img src="{local_rel}" alt="Ilustração" /></div>'
            
    # Unescape HTML entities (&mdash; -> —, etc)
    unescaped = html.unescape(p_raw)
    
    # Parse com BeautifulSoup para balancear tags
    soup = BeautifulSoup(unescaped, 'html.parser')
    
    # Se contiver apenas tags de imagem
    img_tag = soup.find('img')
    if img_tag:
        src = img_tag.get('src')
        if src in local_images_map:
            return f'<div class="illustration-wrap"><img src="{local_images_map[src]}" alt="Ilustração" /></div>'
            
    # Se for quebra de cena com asteriscos ou traço
    text_stripped = soup.get_text(strip=True)
    if text_stripped in ['* * *', '***', '— — —', '♦ ♦ ♦', '◇ ◇ ◇']:
        return '<p class="scene-break">❖ ❖ ❖</p>'
        
    p_content = soup.decode(formatter=None).strip()
    if p_content.startswith('<p>') and p_content.endswith('</p>'):
        p_content = p_content[3:-4].strip()
        
    return f'<p>{p_content}</p>'


def safe_get(session_or_requests, url: str, max_retries: int = 8, timeout: int = 30, initial_backoff: float = 4.0, headers: dict = None) -> requests.Response:
    """
    Executa uma requisição GET com tratamento automático de HTTP 429 (Rate Limit),
    erros de conexão e respostas 5xx de servidor com backoff exponencial e jitter.
    """
    retries = 0
    backoff = initial_backoff
    req_obj = session_or_requests if session_or_requests is not None else requests

    while True:
        try:
            kwargs = {'timeout': timeout}
            if headers:
                kwargs['headers'] = headers

            res = req_obj.get(url, **kwargs)

            if res.status_code == 429:
                retries += 1
                if retries > max_retries:
                    res.raise_for_status()

                # Verifica se o servidor enviou header Retry-After
                retry_after = res.headers.get('Retry-After')
                if retry_after and retry_after.isdigit():
                    wait_time = int(retry_after) + random.uniform(1.0, 3.0)
                else:
                    wait_time = backoff + random.uniform(1.0, 3.0)
                    backoff = min(backoff * 2.0, 60.0)

                print(f"\n[Aviso 429] Limite de requisições do Novel Mania atingido. Aguardando {wait_time:.1f}s antes de tentar novamente... (Tentativa {retries}/{max_retries})")
                time.sleep(wait_time)
                continue

            elif res.status_code in (500, 502, 503, 504):
                retries += 1
                if retries > max_retries:
                    res.raise_for_status()

                wait_time = backoff + random.uniform(0.5, 2.0)
                backoff = min(backoff * 1.5, 30.0)
                print(f"\n[Aviso {res.status_code}] Erro temporário no servidor. Aguardando {wait_time:.1f}s... (Tentativa {retries}/{max_retries})")
                time.sleep(wait_time)
                continue

            if res.status_code != 404:
                res.raise_for_status()

            return res

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            retries += 1
            if retries > max_retries:
                raise
            wait_time = backoff + random.uniform(1.0, 2.5)
            backoff = min(backoff * 1.5, 30.0)
            print(f"\n[Falha de conexão] {e.__class__.__name__}. Aguardando {wait_time:.1f}s... (Tentativa {retries}/{max_retries})")
            time.sleep(wait_time)


def fetch_novel_info(slug: str, session: requests.Session) -> dict:
    """Obtém os dados da obra pela API do Novel Mania."""
    api_url = f"https://novelmania.com.br/api/novels/{slug}"
    print(f"Buscando informações da obra: {api_url} ...")
    r = safe_get(session, api_url, timeout=20)
    if r.status_code == 404:
        raise ValueError(f"Obra '{slug}' não encontrada no Novel Mania (404).")
    data = r.json().get('data', {})
    return data


def fetch_all_chapters_list(slug: str, session: requests.Session) -> list:
    """Busca a lista de todos os capítulos com paginação via API."""
    chapters = []
    page = 1
    limit = 50
    print(f"Buscando lista de capítulos...")
    
    while True:
        url = f"https://novelmania.com.br/api/novels/{slug}/chapters?page={page}&limit={limit}"
        r = safe_get(session, url, timeout=20)
        res = r.json()
        items = res.get('data', [])
        if not items:
            break
        chapters.extend(items)
        meta = res.get('meta', {})
        total_pages = meta.get('pages', 1)
        print(f"  Página {page}/{total_pages} carregada ({len(chapters)}/{meta.get('count', '?')} capítulos)")
        if page >= total_pages:
            break
        page += 1
        time.sleep(random.uniform(0.3, 0.6))
        
    return chapters


def download_and_optimize_image(url: str, dest_path: str, max_width=1600, quality=88):
    """Baixa e otimiza uma imagem para visualização em EPUB."""
    if os.path.exists(dest_path):
        return
    r = safe_get(None, url, headers=HEADERS, timeout=30)
    img = Image.open(io.BytesIO(r.content))
    if img.mode != 'RGB':
        img = img.convert('RGB')
    if img.width > max_width:
        new_height = int(img.height * (max_width / img.width))
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    img.save(dest_path, 'JPEG', quality=quality, optimize=True)
    time.sleep(random.uniform(0.2, 0.5))


def sanitize_filename(name: str) -> str:
    """Gera um nome de arquivo seguro e limpo."""
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    return name.strip()


def build_epub_file(epub_filename: str, book_title: str, book_subtitle: str,
                    author: str, cover_path: str, chapters: list,
                    extra_images: list, local_images_map: dict,
                    synopsis_html: str, categories: list):
    """Monta um arquivo EPUB 3/2 válido a partir dos dados do volume."""
    book_uuid = str(uuid.uuid4())
    
    # 1. Capa
    cover_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="pt-BR" lang="pt-BR">
<head>
    <title>Capa</title>
    <link rel="stylesheet" type="text/css" href="../css/styles.css"/>
    <style type="text/css">
        body {{ margin: 0; padding: 0; text-align: center; background-color: #000; }}
        div.cover-wrapper {{ height: 100vh; display: flex; align-items: center; justify-content: center; }}
        img.cover-img {{ max-width: 100%; max-height: 100vh; height: auto; object-fit: contain; }}
    </style>
</head>
<body>
    <div class="cover-wrapper">
        <img class="cover-img" src="../images/cover.jpg" alt="{html.escape(book_title)}"/>
    </div>
</body>
</html>
"""

    # 2. Página de Título / Metadados
    genres_str = ", ".join([c.get('name', '') for c in categories if isinstance(c, dict)]) if categories else "Light Novel"
    
    clean_synopsis = BeautifulSoup(html.unescape(synopsis_html or ''), 'html.parser').decode(formatter=None) if synopsis_html else '<p>Sem sinopse disponível.</p>'

    titlepage_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="pt-BR" lang="pt-BR">
<head>
    <title>{html.escape(book_title)}</title>
    <link rel="stylesheet" type="text/css" href="../css/styles.css"/>
</head>
<body>
    <span class="volume-tag">NOVEL MANIA</span>
    <h1 class="book-title">{html.escape(book_title)}</h1>
    {f'<h2 class="book-subtitle">{html.escape(book_subtitle)}</h2>' if book_subtitle else ''}
    
    <div class="meta-box">
        <div class="meta-row"><span class="meta-label">Autor:</span> {html.escape(author or "Desconhecido")}</div>
        <div class="meta-row"><span class="meta-label">Fonte:</span> Novel Mania (novelmania.com.br)</div>
        <div class="meta-row"><span class="meta-label">Gênero:</span> {html.escape(genres_str)}</div>
    </div>
    
    <div class="synopsis-box">
        <p><strong>Sinopse:</strong></p>
        {clean_synopsis}
    </div>
</body>
</html>
"""

    # 3. Capítulos
    chapter_files = []
    for c_idx, ch in enumerate(chapters, 1):
        ch_slug = f"chapter_{c_idx:02d}.xhtml"
        ch_title = ch.get('title', f'Capítulo {c_idx}')
        ch_staff = ch.get('staff', '')
        
        body_parts = []
        for p_idx, p_raw in enumerate(ch.get('paragraphs', [])):
            cleaned = clean_paragraph_html(p_raw, local_images_map)
            if p_idx == 0 and cleaned.startswith('<p>'):
                cleaned = '<p class="first">' + cleaned[3:]
            body_parts.append(cleaned)
            
        staff_div = f'<div class="staff-info">{html.escape(ch_staff)}</div>' if ch_staff else '<div class="staff-info" style="border:none;">❖</div>'
        
        ch_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="pt-BR" lang="pt-BR">
<head>
    <title>{html.escape(ch_title)}</title>
    <link rel="stylesheet" type="text/css" href="../css/styles.css"/>
</head>
<body>
    <h1 class="chapter-title">{html.escape(ch_title)}</h1>
    {staff_div}
    
    <div class="chapter-content">
        {"".join(body_parts)}
    </div>
</body>
</html>
"""
        chapter_files.append((ch_slug, ch_title, ch_xhtml, f"chapter_{c_idx:02d}"))

    # 4. TOC Nav (EPUB 3)
    nav_links = ['<li><a href="titlepage.xhtml">Informações da Obra</a></li>']
    for slug, title, _, _ in chapter_files:
        nav_links.append(f'<li><a href="{slug}">{html.escape(title)}</a></li>')
        
    nav_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="pt-BR" lang="pt-BR">
<head>
    <title>Sumário</title>
    <link rel="stylesheet" type="text/css" href="../css/styles.css"/>
</head>
<body>
    <nav epub:type="toc" id="toc">
        <h1 class="chapter-title">Índice</h1>
        <ol>
            {"".join(nav_links)}
        </ol>
    </nav>
</body>
</html>
"""

    # 5. TOC NCX (EPUB 2)
    ncx_navpoints = [f"""
    <navPoint id="np-title" playOrder="1">
        <navLabel><text>Informações da Obra</text></navLabel>
        <content src="text/titlepage.xhtml"/>
    </navPoint>"""]
    for idx, (slug, title, _, _) in enumerate(chapter_files, 2):
        ncx_navpoints.append(f"""
    <navPoint id="np-{idx}" playOrder="{idx}">
        <navLabel><text>{html.escape(title)}</text></navLabel>
        <content src="text/{slug}"/>
    </navPoint>""")
        
    toc_ncx = f"""<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3998/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="urn:uuid:{book_uuid}"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle><text>{html.escape(book_title)}</text></docTitle>
    <docAuthor><text>{html.escape(author or "Desconhecido")}</text></docAuthor>
    <navMap>
        {"".join(ncx_navpoints)}
    </navMap>
</ncx>
"""

    # 6. content.opf
    manifest_items = [
        '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        '<item id="nav" href="text/nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="css" href="css/styles.css" media-type="text/css"/>',
        '<item id="cover-image" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>',
        '<item id="cover" href="text/cover.xhtml" media-type="application/xhtml+xml"/>',
        '<item id="titlepage" href="text/titlepage.xhtml" media-type="application/xhtml+xml"/>',
    ]
    
    spine_items = [
        '<itemref idref="cover"/>',
        '<itemref idref="titlepage"/>',
        '<itemref idref="nav"/>',
    ]
    
    for slug, _, _, item_id in chapter_files:
        manifest_items.append(f'<item id="{item_id}" href="text/{slug}" media-type="application/xhtml+xml"/>')
        spine_items.append(f'<itemref idref="{item_id}"/>')
        
    for _, epub_p, m_type, item_id in extra_images:
        rel_href = epub_p.replace('OEBPS/', '')
        manifest_items.append(f'<item id="{item_id}" href="{rel_href}" media-type="{m_type}"/>')

    content_opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
        <dc:identifier id="BookId">urn:uuid:{book_uuid}</dc:identifier>
        <dc:title>{html.escape(book_title)}</dc:title>
        <dc:creator id="author">{html.escape(author or "Desconhecido")}</dc:creator>
        <meta refines="#author" property="role" scheme="marc:relators">aut</meta>
        <dc:language>pt-BR</dc:language>
        <dc:publisher>Novel Mania</dc:publisher>
        <dc:description>Tradução disponibilizada por Novel Mania (novelmania.com.br).</dc:description>
        <meta name="cover" content="cover-image"/>
        <meta property="dcterms:modified">2026-10-01T16:00:00Z</meta>
    </metadata>
    <manifest>
        {"".join(manifest_items)}
    </manifest>
    <spine toc="ncx">
        {"".join(spine_items)}
    </spine>
    <guide>
        <reference type="cover" title="Capa" href="text/cover.xhtml"/>
        <reference type="title-page" title="Página de Título" href="text/titlepage.xhtml"/>
        <reference type="toc" title="Sumário" href="text/nav.xhtml"/>
    </guide>
</package>
"""

    container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>
"""

    # 7. Escrita do arquivo ZIP (.epub)
    with zipfile.ZipFile(epub_filename, 'w') as zf:
        zf.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        zf.writestr('META-INF/container.xml', container_xml, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr('OEBPS/content.opf', content_opf, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr('OEBPS/toc.ncx', toc_ncx, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr('OEBPS/nav.xhtml', nav_xhtml, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr('OEBPS/css/styles.css', CSS_STYLE, compress_type=zipfile.ZIP_DEFLATED)
        with open(cover_path, 'rb') as f:
            zf.writestr('OEBPS/images/cover.jpg', f.read(), compress_type=zipfile.ZIP_DEFLATED)
        for disk_p, epub_p, _, _ in extra_images:
            if os.path.exists(disk_p):
                with open(disk_p, 'rb') as f:
                    zf.writestr(epub_p, f.read(), compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr('OEBPS/text/cover.xhtml', cover_xhtml, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr('OEBPS/text/titlepage.xhtml', titlepage_xhtml, compress_type=zipfile.ZIP_DEFLATED)
        for slug, _, xhtml_c, _ in chapter_files:
            zf.writestr(f'OEBPS/text/{slug}', xhtml_c, compress_type=zipfile.ZIP_DEFLATED)


def process_novel(slug: str):
    """Orquestra o download e a compilação em EPUB para a obra informada."""
    session = requests.Session()
    session.headers.update(HEADERS)
    
    # Normaliza o slug caso o usuário passe com 'epub_'
    clean_slug = slug[5:] if slug.startswith('epub_') else slug
    slug = clean_slug
    
    # Pastas da obra (prefixadas com epub_)
    novel_dir = f"epub_{slug}"
    cache_chapters_dir = os.path.join(novel_dir, '.cache_chapters')
    cache_covers_dir = os.path.join(novel_dir, '.cache_covers')
    cache_images_dir = os.path.join(novel_dir, '.cache_images')
    output_dir = os.path.join(novel_dir, 'novel')
    
    os.makedirs(novel_dir, exist_ok=True)
    os.makedirs(cache_chapters_dir, exist_ok=True)
    os.makedirs(cache_covers_dir, exist_ok=True)
    os.makedirs(cache_images_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n========================================================")
    print(f"Iniciando processamento da obra: {slug}")
    print(f"Diretório de saída: {output_dir}")
    print(f"========================================================")
    
    # 1. Informações da Novel
    novel_info_file = os.path.join(cache_chapters_dir, 'novel_info.json')
    if os.path.exists(novel_info_file):
        with open(novel_info_file, 'r', encoding='utf-8') as f:
            novel_data = json.load(f)
    else:
        novel_data = fetch_novel_info(slug, session)
        with open(novel_info_file, 'w', encoding='utf-8') as f:
            json.dump(novel_data, f, indent=2, ensure_ascii=False)
            
    novel_title = novel_data.get('title', slug)
    author = novel_data.get('author', 'Desconhecido')
    synopsis = novel_data.get('synopsis', '')
    categories = novel_data.get('categories', [])
    cover_urls = novel_data.get('cover', {})
    main_cover_url = cover_urls.get('original') or cover_urls.get('large') or cover_urls.get('small')
    
    # Baixar capa principal
    main_cover_path = os.path.join(cache_covers_dir, 'main_cover.jpg')
    if main_cover_url and not os.path.exists(main_cover_path):
        print("Baixando capa principal...")
        try:
            download_and_optimize_image(main_cover_url, main_cover_path)
        except Exception as e:
            print(f"Aviso ao baixar capa: {e}")
            
    # 2. Lista de Capítulos
    chapters_list_file = os.path.join(cache_chapters_dir, 'chapters_list.json')
    if os.path.exists(chapters_list_file):
        with open(chapters_list_file, 'r', encoding='utf-8') as f:
            chapters_meta = json.load(f)
    else:
        chapters_meta = fetch_all_chapters_list(slug, session)
        with open(chapters_list_file, 'w', encoding='utf-8') as f:
            json.dump(chapters_meta, f, indent=2, ensure_ascii=False)
            
    print(f"Total de capítulos encontrados: {len(chapters_meta)}")
    if not chapters_meta:
        print("Nenhum capítulo encontrado para esta obra.")
        return

    # 3. Baixar e extrair conteúdo de cada capítulo
    chapters_content_file = os.path.join(cache_chapters_dir, 'chapters_data.json')
    chapters_data = []
    if os.path.exists(chapters_content_file):
        with open(chapters_content_file, 'r', encoding='utf-8') as f:
            chapters_data = json.load(f)
            
    cached_slugs = {c['slug']: c for c in chapters_data}
    
    meta_by_slug = {c.get('slug'): c for c in chapters_meta if c.get('slug')}
    
    print("\nVerificando/baixando conteúdo dos capítulos...")
    updated_data = []
    
    for idx, ch_meta in enumerate(chapters_meta, 1):
        ch_slug = ch_meta.get('slug')
        if not ch_slug:
            continue
            
        cached_entry = cached_slugs.get(ch_slug)
        
        # Determina o nome do volume
        unity = ch_meta.get('unity') or {}
        unity_name = unity.get('name') if isinstance(unity, dict) else None
        if not unity_name and cached_entry and cached_entry.get('volume'):
            unity_name = f"Volume {cached_entry['volume']}"
            
        if not unity_name:
            m_vol = re.search(r'volume-(\d+|unico)', ch_slug, re.IGNORECASE)
            if m_vol:
                v_str = m_vol.group(1).lower()
                unity_name = f"Volume {v_str.capitalize()}" if v_str != 'unico' else "Volume Único"
            else:
                unity_name = "Volume Único"

        if cached_entry:
            cached_entry['volume_name'] = unity_name
            cached_entry['unity_title'] = unity.get('title') if isinstance(unity, dict) else None
            updated_data.append(cached_entry)
            continue
            
        ch_url = f"https://novelmania.com.br/novels/{slug}/capitulos/{ch_slug}"
        raw_html_path = os.path.join(cache_chapters_dir, f"{ch_slug}.html")
        
        if os.path.exists(raw_html_path):
            with open(raw_html_path, 'r', encoding='utf-8') as f:
                ch_html = f.read()
        else:
            print(f"[{idx}/{len(chapters_meta)}] Baixando capítulo: {ch_meta.get('title') or ch_slug}...")
            res = safe_get(session, ch_url, timeout=25)
            ch_html = res.text
            with open(raw_html_path, 'w', encoding='utf-8') as f:
                f.write(ch_html)
            # Intervalo inteligente para respeitar o rate-limit do servidor
            time.sleep(random.uniform(0.7, 1.3))
            
        soup = BeautifulSoup(ch_html, 'lxml')
        
        # Título
        h1 = soup.find('h1')
        if h1:
            for sr in h1.find_all(class_='sr-only'):
                sr.decompose()
            title = h1.get_text(strip=True)
        else:
            title = ch_meta.get('title', ch_slug)
            
        # Staff (tradutor / revisor)
        translators = [t.get('username') for t in ch_meta.get('translators', []) if t.get('username')]
        editors = [e.get('username') for e in ch_meta.get('editors', []) if e.get('username')]
        staff_parts = []
        if translators:
            staff_parts.append(f"Tradução: {', '.join(translators)}")
        if editors:
            staff_parts.append(f"Revisão: {', '.join(editors)}")
        staff = " | ".join(staff_parts)
        
        # Conteúdo do capítulo
        body = soup.find(class_=lambda x: x and 'rich-text-content' in x and 'prose' in x)
        paragraphs = []
        images = []
        if body:
            for s in body.find_all(['script', 'style']):
                s.decompose()
            for img in body.find_all('img'):
                src = img.get('src')
                if src:
                    images.append(src)
            for child in body.children:
                if child.name == 'p':
                    p_text = child.decode_contents().strip()
                    if p_text and p_text != '&nbsp;':
                        paragraphs.append(p_text)
                elif child.name in ['h2', 'h3', 'h4', 'blockquote', 'hr']:
                    paragraphs.append(f"<{child.name}>{child.decode_contents().strip()}</{child.name}>")
                elif child.name == 'div' and child.find('img'):
                    for im in child.find_all('img'):
                        paragraphs.append(f'<p><img src="{im.get("src")}" /></p>')

        unity = ch_meta.get('unity') or {}
        unity_name = unity.get('name') if isinstance(unity, dict) else None
        
        # Tenta inferir volume do slug caso não conste na unity
        if not unity_name:
            m_vol = re.search(r'volume-(\d+|unico)', ch_slug, re.IGNORECASE)
            if m_vol:
                v_str = m_vol.group(1).lower()
                unity_name = f"Volume {v_str.capitalize()}" if v_str != 'unico' else "Volume Único"
            else:
                unity_name = "Volume Único"

        entry = {
            'index': idx,
            'slug': ch_slug,
            'title': title,
            'staff': staff,
            'volume_name': unity_name,
            'paragraphs': paragraphs,
            'images': images
        }
        updated_data.append(entry)

        # Salva o progresso a cada 10 capítulos
        if idx % 10 == 0:
            with open(chapters_content_file, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, indent=2, ensure_ascii=False)
        
    with open(chapters_content_file, 'w', encoding='utf-8') as f:
        json.dump(updated_data, f, indent=2, ensure_ascii=False)
        
    print(f"Todos os {len(updated_data)} capítulos foram processados.")

    # 4. Baixar imagens internas encontradas nos capítulos
    local_images_map = {}
    extra_images = []
    
    img_counter = 1
    for ch in updated_data:
        for img_url in ch.get('images', []):
            if img_url not in local_images_map:
                img_name = f"ill_{img_counter:03d}.jpg"
                img_disk_path = os.path.join(cache_images_dir, img_name)
                try:
                    download_and_optimize_image(img_url, img_disk_path)
                    epub_internal_path = f"OEBPS/images/{img_name}"
                    local_images_map[img_url] = f"../images/{img_name}"
                    extra_images.append((img_disk_path, epub_internal_path, "image/jpeg", f"img_{img_counter}"))
                    img_counter += 1
                except Exception as e:
                    print(f"Aviso ao baixar imagem {img_url}: {e}")

    # 5. Agrupar por volume e compilar EPUBs
    volumes = {}
    for ch in updated_data:
        v_name = ch.get('volume_name') or 'Volume Único'
        volumes.setdefault(v_name, []).append(ch)
        
    print(f"\nAgrupados em {len(volumes)} volume(s):")
    for v_name, chs in volumes.items():
        print(f"  • {v_name}: {len(chs)} capítulos")
        
    known_subtitles_map = {
        'hyouka': {
            1: {'subtitle': 'The niece of time', 'pt_title': 'Hyouka'},
            2: {'subtitle': "Why didn't she ask Eba?", 'pt_title': 'O Fim de Jogo do Tolo'},
            3: {'subtitle': 'Welcome to Kanya Festa!', 'pt_title': 'A Ordem de Kudryavka'},
            4: {'subtitle': 'Little birds can remember', 'pt_title': 'A Boneca que Faz Desvio'},
            5: {'subtitle': 'It walks by past', 'pt_title': 'A Estimativa da Distancia entre Dois'},
            6: {'subtitle': "Even Though I'm Told Now That I Have Wings", 'pt_title': 'Mesmo Que Me Digam Que Agora Tenho Asas'},
        }
    }

    for v_name, v_chapters in volumes.items():
        # Define nome do arquivo e capa
        vol_num_m = re.search(r'\d+', v_name)
        vol_num = int(vol_num_m.group(0)) if vol_num_m else None
        
        known_info = known_subtitles_map.get(slug, {}).get(vol_num, {}) if vol_num else {}
        extra_sub = known_info.get('subtitle')
        pt_vol_name = known_info.get('pt_title')
        
        v_slug_clean = sanitize_filename(v_name)
        short_title = "Hyouka" if slug == "hyouka" else sanitize_filename(novel_title)
        
        if len(volumes) == 1:
            epub_fname = f"{short_title}.epub"
            vol_title = novel_title
            vol_subtitle = ""
        else:
            if pt_vol_name and vol_num != 1:
                epub_fname = f"{short_title} - {v_slug_clean} - {pt_vol_name}.epub"
                vol_title = f"{short_title}: {pt_vol_name} ({v_name})"
            else:
                epub_fname = f"{short_title} - {v_slug_clean}.epub"
                vol_title = f"{short_title} - {v_name}"
            vol_subtitle = extra_sub or v_name
            
        epub_out_path = os.path.join(output_dir, epub_fname)
        
        # Verifica se existe capa específica do volume salva no cache
        vol_cover = None
        if vol_num:
            specific_cover = os.path.join(cache_covers_dir, f"volume_{vol_num}_cover.jpg")
            if os.path.exists(specific_cover):
                vol_cover = specific_cover
                
        if not vol_cover:
            vol_cover = main_cover_path
            
        print(f"\nGerando EPUB: {epub_fname} ({len(v_chapters)} capítulos)...")
        build_epub_file(
            epub_filename=epub_out_path,
            book_title=vol_title,
            book_subtitle=vol_subtitle,
            author=author,
            cover_path=vol_cover,
            chapters=v_chapters,
            extra_images=extra_images,
            local_images_map=local_images_map,
            synopsis_html=synopsis,
            categories=categories
        )
        size_mb = os.path.getsize(epub_out_path) / (1024 * 1024)
        print(f"-> Sucesso! Arquivo gerado: {epub_out_path} ({size_mb:.2f} MB)")

    print(f"\nPronto! Todos os EPUBs foram criados em '{output_dir}'.")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python generate_novel.py <slug>")
        print("Exemplo: python generate_novel.py hyouka")
        sys.exit(1)
        
    target_slug = sys.argv[1].strip().lower()
    process_novel(target_slug)
