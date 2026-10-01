#!/usr/bin/env python3
"""
Aplicação Web FastAPI para o Novel Mania to EPUB.
Pode ser executada localmente ou no Hugging Face Spaces (porta 7860).
"""

import os
import io
import re
import zipfile
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from generate_novel import process_novel, HEADERS

app = FastAPI(
    title="Novel Mania to EPUB",
    description="Baixe novels do Novel Mania em arquivos EPUB organizados por volume e compactados em ZIP.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_slug(input_str: str) -> str:
    """Extrai o slug limpo mesmo se o usuário colar uma URL completa."""
    if not input_str:
        return ""
    input_str = input_str.strip().rstrip('/')
    if 'novelmania.com.br/novels/' in input_str:
        input_str = input_str.split('novelmania.com.br/novels/')[-1]
    input_str = input_str.split('/')[0]
    if input_str.startswith('epub_'):
        input_str = input_str[5:]
    return input_str.lower()


HTML_PAGE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Novel Mania to EPUB</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0f1117;
            --card-bg: #1a1d27;
            --card-border: #2a2f42;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --accent: #10b981;
            --tag-bg: #282e44;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 20px;
        }

        .container {
            width: 100%;
            max-width: 680px;
        }

        .header {
            text-align: center;
            margin-bottom: 36px;
        }

        .badge {
            display: inline-block;
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(16, 185, 129, 0.2));
            color: #a5b4fc;
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 0.82rem;
            font-weight: 600;
            margin-bottom: 14px;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }

        h1 {
            font-size: 2.3rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-bottom: 10px;
            background: linear-gradient(to right, #ffffff, #c7d2fe);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        p.subtitle {
            color: var(--text-muted);
            font-size: 1.05rem;
            line-height: 1.5;
        }

        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 28px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
            margin-bottom: 24px;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-bottom: 20px;
        }

        label {
            font-size: 0.9rem;
            font-weight: 600;
            color: #d1d5db;
        }

        .input-row {
            display: flex;
            gap: 12px;
        }

        input[type="text"] {
            flex: 1;
            padding: 14px 18px;
            border-radius: 10px;
            border: 1px solid var(--card-border);
            background-color: #12141c;
            color: #ffffff;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        input[type="text"]:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.25);
        }

        button.btn-primary {
            padding: 14px 24px;
            background: linear-gradient(135deg, var(--primary), var(--primary-hover));
            color: white;
            font-weight: 600;
            font-size: 1rem;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: transform 0.15s, opacity 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
            white-space: nowrap;
        }

        button.btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45);
        }

        button.btn-primary:active {
            transform: translateY(0);
        }

        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none !important;
        }

        .quick-links {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
            font-size: 0.85rem;
            color: var(--text-muted);
        }

        .chip {
            background-color: var(--tag-bg);
            color: #c7d2fe;
            border: 1px solid rgba(99, 102, 241, 0.2);
            padding: 4px 10px;
            border-radius: 6px;
            cursor: pointer;
            transition: background-color 0.15s;
        }

        .chip:hover {
            background-color: rgba(99, 102, 241, 0.25);
        }

        /* Preview Card */
        #preview-card {
            display: none;
            margin-top: 24px;
            padding-top: 20px;
            border-top: 1px solid var(--card-border);
        }

        .preview-content {
            display: flex;
            gap: 20px;
            align-items: flex-start;
        }

        .preview-cover {
            width: 100px;
            height: 145px;
            object-fit: cover;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
            flex-shrink: 0;
            background-color: #222;
        }

        .preview-info {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .preview-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: #ffffff;
        }

        .preview-meta {
            font-size: 0.88rem;
            color: var(--text-muted);
        }

        .preview-genres {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 6px;
        }

        .genre-badge {
            background: #252a3b;
            color: #a5b4fc;
            font-size: 0.75rem;
            padding: 2px 8px;
            border-radius: 4px;
        }

        /* Status & Spinner */
        #status-area {
            display: none;
            margin-top: 20px;
            padding: 16px;
            border-radius: 10px;
            background: rgba(99, 102, 241, 0.08);
            border: 1px solid rgba(99, 102, 241, 0.25);
            text-align: center;
            font-size: 0.95rem;
        }

        .spinner {
            display: inline-block;
            width: 18px;
            height: 18px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: #ffffff;
            animation: spin 0.8s ease-in-out infinite;
            vertical-align: middle;
            margin-right: 8px;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-top: 12px;
        }

        .feature-item {
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 18px;
            border-radius: 12px;
            font-size: 0.88rem;
            line-height: 1.5;
        }

        .feature-item strong {
            display: block;
            color: #ffffff;
            margin-bottom: 4px;
            font-size: 0.95rem;
        }

        .feature-item span {
            color: var(--text-muted);
        }

        footer {
            margin-top: 40px;
            color: #6b7280;
            font-size: 0.85rem;
            text-align: center;
        }

        footer a {
            color: #818cf8;
            text-decoration: none;
        }

        @media (max-width: 600px) {
            .input-row {
                flex-direction: column;
            }
            .preview-content {
                flex-direction: column;
                align-items: center;
                text-align: center;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="badge">EPUB 3 / Kindle Ready</span>
            <h1>Novel Mania to EPUB</h1>
            <p class="subtitle">Insira o slug ou link da obra para gerar os arquivos EPUB divididos por volume e baixar em um arquivo ZIP.</p>
        </div>

        <div class="card">
            <div class="form-group">
                <label for="slug-input">Slug ou Link da Novel:</label>
                <div class="input-row">
                    <input type="text" id="slug-input" placeholder="ex: hyouka ou amor-invisivel-sob-o-ceu-noturno" autofocus />
                    <button class="btn-primary" id="btn-download" onclick="startDownload()">
                        <span id="btn-icon">📥</span>
                        <span id="btn-text">Baixar ZIP</span>
                    </button>
                </div>
            </div>

            <div class="quick-links">
                <span>Sugestões:</span>
                <span class="chip" onclick="setSlug('hyouka')">hyouka</span>
                <span class="chip" onclick="setSlug('amor-invisivel-sob-o-ceu-noturno')">amor-invisivel</span>
                <span class="chip" onclick="setSlug('5-centimetros-por-segundo')">5-centimetros</span>
            </div>

            <div id="status-area"></div>

            <div id="preview-card">
                <div class="preview-content">
                    <img id="preview-img" class="preview-cover" src="" alt="Capa" />
                    <div class="preview-info">
                        <div id="preview-title" class="preview-title"></div>
                        <div id="preview-author" class="preview-meta"></div>
                        <div id="preview-chapters" class="preview-meta"></div>
                        <div id="preview-genres" class="preview-genres"></div>
                    </div>
                </div>
            </div>
        </div>

        <div class="features-grid">
            <div class="feature-item">
                <strong>📖 Organizado por Volume</strong>
                <span>Agrupa automaticamente os capítulos em volumes completos e títulos oficiais.</span>
            </div>
            <div class="feature-item">
                <strong>🖼️ Capas e Ilustrações</strong>
                <span>Baixa e incorpora ilustrações internas no livro para leitura 100% offline.</span>
            </div>
            <div class="feature-item">
                <strong>📱 Compatível com Tudo</strong>
                <span>Padrão duplo EPUB 3/2 pronto para Kindle, Kobo, Apple Books e Moon+ Reader.</span>
            </div>
        </div>

        <footer>
            Novel Mania to EPUB • Código aberto no <a href="https://github.com/0xBlooD/novelmania_to_epub" target="_blank">GitHub</a>
        </footer>
    </div>

    <script>
        let previewTimeout = null;

        function setSlug(val) {
            document.getElementById('slug-input').value = val;
            checkPreview();
        }

        document.getElementById('slug-input').addEventListener('input', () => {
            clearTimeout(previewTimeout);
            previewTimeout = setTimeout(checkPreview, 500);
        });

        async function checkPreview() {
            const raw = document.getElementById('slug-input').value.trim();
            if (!raw) {
                document.getElementById('preview-card').style.display = 'none';
                return;
            }

            try {
                const res = await fetch(`/api/info?slug=${encodeURIComponent(raw)}`);
                if (!res.ok) {
                    document.getElementById('preview-card').style.display = 'none';
                    return;
                }
                const data = await res.json();
                document.getElementById('preview-title').textContent = data.title || raw;
                document.getElementById('preview-author').textContent = 'Autor: ' + (data.author || 'Desconhecido');
                document.getElementById('preview-chapters').textContent = 'Total: ' + (data.chaptersCount || '?') + ' capítulos';
                document.getElementById('preview-img').src = data.coverUrl || '';

                const genresDiv = document.getElementById('preview-genres');
                genresDiv.innerHTML = '';
                (data.categories || []).forEach(cat => {
                    const span = document.createElement('span');
                    span.className = 'genre-badge';
                    span.textContent = cat;
                    genresDiv.appendChild(span);
                });

                document.getElementById('preview-card').style.display = 'block';
            } catch (err) {
                document.getElementById('preview-card').style.display = 'none';
            }
        }

        async function startDownload() {
            const raw = document.getElementById('slug-input').value.trim();
            if (!raw) {
                alert('Por favor, informe o slug da novel.');
                return;
            }

            const btn = document.getElementById('btn-download');
            const status = document.getElementById('status-area');
            const btnText = document.getElementById('btn-text');
            const btnIcon = document.getElementById('btn-icon');

            btn.disabled = true;
            btnIcon.innerHTML = '<span class="spinner"></span>';
            btnText.textContent = 'Processando...';

            status.style.display = 'block';
            status.innerHTML = '⏳ <strong>Baixando capítulos e compilando EPUBs...</strong><br><small style="color:var(--text-muted)">Isso pode levar de 15 a 45 segundos dependendo do tamanho da novel.</small>';

            try {
                // Inicia o download direcionando o navegador para o endpoint de download
                const downloadUrl = `/api/download?slug=${encodeURIComponent(raw)}`;
                
                // Dispara o download via iframe invisível ou link
                const link = document.createElement('a');
                link.href = downloadUrl;
                link.setAttribute('download', '');
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);

                status.innerHTML = '✨ <strong>Download iniciado!</strong> Verifique a pasta de downloads do seu navegador.';
            } catch (err) {
                status.innerHTML = '❌ <strong>Erro:</strong> ' + err.message;
            } finally {
                setTimeout(() => {
                    btn.disabled = false;
                    btnIcon.textContent = '📥';
                    btnText.textContent = 'Baixar ZIP';
                }, 4000);
            }
        }
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=HTML_PAGE)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/info")
def get_info(slug: str = Query(..., description="Slug ou link da novel")):
    clean = extract_slug(slug)
    if not clean:
        raise HTTPException(status_code=400, detail="Slug inválido.")
        
    api_url = f"https://novelmania.com.br/api/novels/{clean}"
    try:
        r = requests.get(api_url, headers=HEADERS, timeout=10)
        if r.status_code == 404:
            raise HTTPException(status_code=404, detail="Novel não encontrada.")
        r.raise_for_status()
        data = r.json().get('data', {})
        
        cover_info = data.get('cover', {})
        cover_url = cover_info.get('small') or cover_info.get('large') or cover_info.get('original')
        categories = [c.get('name') for c in data.get('categories', []) if isinstance(c, dict)]
        
        return {
            "slug": clean,
            "title": data.get('title'),
            "author": data.get('author'),
            "chaptersCount": data.get('chaptersCount'),
            "coverUrl": cover_url,
            "categories": categories
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar API: {str(e)}")


@app.get("/api/download")
@app.get("/download")
def download_novel_zip(slug: str = Query(..., description="Slug ou link da novel")):
    clean = extract_slug(slug)
    if not clean:
        raise HTTPException(status_code=400, detail="Slug inválido.")
        
    try:
        # Executa o processamento e compilação dos EPUBs
        process_novel(clean)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar novel '{clean}': {str(e)}")
        
    novel_folder = f"epub_{clean}/novel"
    if not os.path.exists(novel_folder):
        raise HTTPException(status_code=404, detail="Nenhum arquivo EPUB foi gerado.")
        
    epub_files = [f for f in os.listdir(novel_folder) if f.endswith('.epub')]
    if not epub_files:
        raise HTTPException(status_code=404, detail="Pasta de EPUBs vazia.")
        
    # Compacta todos os .epub da pasta em memória
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(epub_files):
            full_p = os.path.join(novel_folder, f)
            zf.write(full_p, arcname=f)
            
    zip_buffer.seek(0)
    
    zip_filename = f"{clean}_epubs.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"',
            "Content-Type": "application/zip"
        }
    )


if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
