#!/usr/bin/env python3
"""
Lele - Application d'analyse qualitative de données (QDA)

Point d'entrée principal de l'application.
"""

import sys


def main():
    """Lance l'application Lele."""
    from lele.ui import MainWindow

    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
