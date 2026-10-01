#!/usr/bin/env python3
"""
Aplicação Web Gradio para o Novel Mania to EPUB.
Pronta para execução local ou no Hugging Face Spaces (Gradio SDK).
"""

import os
import io
import re
import zipfile
import requests
import gradio as gr
from generate_novel import process_novel, HEADERS, safe_get

# Compatibilidade com Hugging Face ZeroGPU (evita o erro 'No @spaces.GPU function detected')
try:
    import spaces
    @spaces.GPU
    def _zerogpu_startup():
        return True
except Exception:
    pass


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


def fetch_preview(slug_or_url: str):
    """Busca informações da novel para exibição prévia."""
    slug = extract_slug(slug_or_url)
    if not slug:
        return None, "Por favor, informe o slug ou link da obra.", ""

    api_url = f"https://novelmania.com.br/api/novels/{slug}"
    try:
        r = safe_get(None, api_url, headers=HEADERS, timeout=10)
        if r.status_code == 404:
            return None, f"❌ Obra '{slug}' não encontrada no Novel Mania (404).", ""
        data = r.json().get('data', {})

        title = data.get('title', slug)
        author = data.get('author', 'Desconhecido')
        count = data.get('chaptersCount', '?')
        categories = [c.get('name') for c in data.get('categories', []) if isinstance(c, dict)]
        genres_str = " • ".join(categories) if categories else "Light Novel"

        cover_info = data.get('cover', {})
        cover_url = cover_info.get('large') or cover_info.get('original') or cover_info.get('small')

        details_md = f"""### 📖 {title}
**Autor:** {author}  
**Total de Capítulos:** {count}  
**Gêneros:** {genres_str}  
"""
        return cover_url, details_md, slug
    except Exception as e:
        return None, f"Aviso ao consultar metadados: {e}", slug


def generate_epubs_and_zip(slug_or_url: str, progress=gr.Progress()):
    """Executa a geração dos EPUBs e retorna o arquivo ZIP para download."""
    slug = extract_slug(slug_or_url)
    if not slug:
        return None, "❌ Informe um slug ou link válido."

    progress(0.1, desc="Consultando informações da novel...")
    try:
        progress(0.3, desc="Baixando capítulos e ilustrações...")
        process_novel(slug)
    except Exception as e:
        return None, f"❌ Erro durante o processamento da obra: {str(e)}"

    novel_folder = f"epub_{slug}/novel"
    if not os.path.exists(novel_folder):
        return None, "❌ Falha: A pasta com os EPUBs gerados não foi encontrada."

    epub_files = [f for f in os.listdir(novel_folder) if f.endswith('.epub')]
    if not epub_files:
        return None, "❌ Nenhum arquivo EPUB encontrado."

    progress(0.8, desc="Compactando arquivos EPUB em arquivo ZIP...")
    zip_path = f"epub_{slug}/{slug}_epubs.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(epub_files):
            full_p = os.path.join(novel_folder, f)
            zf.write(full_p, arcname=f)

    progress(1.0, desc="Concluído!")
    msg = f"✨ **Sucesso!** {len(epub_files)} volume(s) EPUB gerados com sucesso."
    return zip_path, msg


CUSTOM_CSS = """
.gradio-container {
    max-width: 800px !important;
    margin: auto !important;
}
#preview-cover img {
    max-height: 220px !important;
    object-fit: cover !important;
    border-radius: 8px !important;
}
"""

with gr.Blocks(title="Novel Mania to EPUB") as demo:
    gr.Markdown("""
    # 📚 Novel Mania to EPUB Generator
    Gere arquivos **EPUB** de alta qualidade das obras traduzidas no [Novel Mania](https://novelmania.com.br).
    Os capítulos são divididos por volume, com capas em alta definição, ilustrações embutidas e padrão duplo EPUB 3 / EPUB 2.
    """)

    with gr.Row():
        slug_input = gr.Textbox(
            label="Slug ou Link da Novel",
            placeholder="Ex: hyouka ou amor-invisivel-sob-o-ceu-noturno",
            scale=4
        )
        btn_preview = gr.Button("🔍 Ver Prévia", scale=1)

    with gr.Row():
        preview_cover = gr.Image(label="Capa", elem_id="preview-cover", scale=1, visible=False)
        preview_details = gr.Markdown(visible=False, scale=2)

    hidden_slug = gr.Textbox(visible=False)

    with gr.Row():
        btn_generate = gr.Button("🚀 Gerar e Baixar EPUBs (.zip)", variant="primary", scale=2)

    status_output = gr.Markdown()
    file_output = gr.File(label="📦 Download do Arquivo ZIP com os EPUBs")

    gr.Examples(
        examples=[
            ["hyouka"],
            ["amor-invisivel-sob-o-ceu-noturno"],
            ["5-centimetros-por-segundo"]
        ],
        inputs=slug_input,
        label="Exemplos Populares (clique para preencher):"
    )

    def on_preview_click(slug_text):
        cover, details, slug = fetch_preview(slug_text)
        if cover:
            return gr.update(value=cover, visible=True), gr.update(value=details, visible=True), slug
        elif details:
            return gr.update(visible=False), gr.update(value=details, visible=True), slug
        return gr.update(visible=False), gr.update(visible=False), slug

    btn_preview.click(
        fn=on_preview_click,
        inputs=slug_input,
        outputs=[preview_cover, preview_details, hidden_slug]
    )

    btn_generate.click(
        fn=generate_epubs_and_zip,
        inputs=slug_input,
        outputs=[file_output, status_output]
    )

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port, theme=gr.themes.Soft(), css=CUSTOM_CSS)
else:
    # Quando o Hugging Face importa como módulo
    demo.theme = gr.themes.Soft()
    demo.css = CUSTOM_CSS
