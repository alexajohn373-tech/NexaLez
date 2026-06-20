"""Application entry point."""

from gui import LexicalAnalyzerGUI


def main() -> None:
    app = LexicalAnalyzerGUI()
    app.mainloop()


if __name__ == "__main__":
    main()

