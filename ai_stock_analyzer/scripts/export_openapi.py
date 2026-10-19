"""Run from the backend directory: python -m scripts.export_openapi."""

from pathlib import Path

import yaml

from app.main import app


def main():
    destination = Path(__file__).resolve().parents[1] / "docs" / "openapi.yaml"
    destination.write_text(
        "# Generated from app.main:app; regenerate with python -m scripts.export_openapi.\n"
        + yaml.safe_dump(app.openapi(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print("Updated docs/openapi.yaml")


if __name__ == "__main__":
    main()
