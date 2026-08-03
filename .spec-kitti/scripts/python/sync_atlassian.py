#!/usr/bin/env python3
"""
Wrapper para ejecutar el sync de Atlassian desde scripts de bash/powershell
"""

import sys
from pathlib import Path

# Estructura: .spec-kitti/scripts/python/sync_atlassian.py
# parent       = .spec-kitti/scripts/python/
# parent.parent = .spec-kitti/scripts/
# parent.parent.parent = .spec-kitti/
# → src está en .spec-kitti/src/
src_path = Path(__file__).resolve().parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from atlassian_sync.cli.sync import main

if __name__ == '__main__':
    sys.exit(main())

