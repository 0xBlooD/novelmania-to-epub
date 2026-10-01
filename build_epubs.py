#!/usr/bin/env python3
"""
Atalho para compilar Hyouka ou qualquer obra informada.
Uso:
    python build_epubs.py [slug]
Se nenhum slug for informado, processa 'hyouka' por padrão.
"""

import sys
from generate_novel import process_novel

if __name__ == '__main__':
    target = sys.argv[1].strip().lower() if len(sys.argv) > 1 else 'hyouka'
    process_novel(target)
