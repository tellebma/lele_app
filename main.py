#!/usr/bin/env python3
"""
Lele - Application d'analyse qualitative de données (QDA)

Point d'entrée principal de l'application.
"""

import sys


def main():
    """Lance l'application Lele."""
    # Initialiser le logging
    from lele import setup_logging
    setup_logging()

    # Logger les informations système au démarrage
    from lele.utils.system import log_system_info
    log_system_info()

    # Lancer l'interface
    from lele.ui import MainWindow
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
