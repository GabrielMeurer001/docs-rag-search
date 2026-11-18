import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .config import ROOT, Settings
from .evaluation import evaluate
from .markdown import load_documents
from .models import LocalModels
from .service import DEPENDENCY_ERRORS
from .store import Store


def main():
    parser = argparse.ArgumentParser(description="Operações locais do docs-rag-search")
    commands = parser.add_subparsers(dest="command", required=True)
    index = commands.add_parser("index", help="Indexar os documentos do manifesto")
    index.add_argument("--manifest", type=Path, default=ROOT / "corpus" / "manifest.json")
    evaluation = commands.add_parser("evaluate", help="Medir recuperação e registrar respostas para revisão")
    evaluation.add_argument("--questions", type=Path, default=ROOT / "evaluation" / "questions.json")
    evaluation.add_argument("--output", type=Path)
    args = parser.parse_args()
    settings = Settings.from_env()
    store = Store(settings.database_url)
    models = LocalModels(settings)
    try:
        if args.command == "index":
            stats = store.index(load_documents(args.manifest), models)
            print(json.dumps(asdict(stats), ensure_ascii=False))
        else:
            report = evaluate(args.questions, store, models)
            content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            if args.output:
                args.output.write_text(content, encoding="utf-8")
                print(f"Avaliação gravada em {args.output}")
            else:
                print(content, end="")
            return 0 if report["automatic_checks_passed"] else 1
    except (OSError, ValueError, KeyError, *DEPENDENCY_ERRORS) as exc:
        print(f"Falha em {args.command}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
