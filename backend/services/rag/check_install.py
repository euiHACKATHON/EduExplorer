"""Check that the backend's packages are installed and that curriculum search works.

    python -m backend.services.rag.check_install

Run it from the project root (the folder that contains `backend/`).
"""
import importlib
import sys
from importlib import metadata

REQUIRED = {
    'fastapi': 'fastapi', 'uvicorn': 'uvicorn', 'pydantic': 'pydantic', 'dotenv': 'python-dotenv',
    'httpx': 'httpx', 'pytest': 'pytest', 'langgraph': 'langgraph', 'langchain_core': 'langchain-core',
    'langchain_groq': 'langchain-groq', 'groq': 'groq',
}
OPTIONAL = {
    'pypdf': 'pypdf  (reading PDF uploads)',
    'sentence_transformers': 'sentence-transformers  (semantic search)',
}


def _check(table: dict[str, str]) -> list[str]:
    missing = []
    for module, label in table.items():
        package = label.split()[0]
        try:
            importlib.import_module(module)
            try:
                version = metadata.version(package)
            except metadata.PackageNotFoundError:
                version = '?'
            print(f'  OK       {label:<52} {version}')
        except Exception as exc:
            print(f'  MISSING  {label:<52} ({type(exc).__name__})')
            missing.append(package)
    return missing


def main() -> int:
    print(f'Python {sys.version.split()[0]}  ({sys.executable})\n')
    print('Required packages (backend/requirements.txt):')
    missing = _check(REQUIRED)
    print('\nOptional packages (backend/requirements-rag.txt):')
    missing_opt = _check(OPTIONAL)
    if missing:
        print('\nInstall what is missing with:\n  python -m pip install -r backend/requirements.txt')
        return 1

    print('\nBuilding the curriculum index (the first run with sentence-transformers downloads a ~90 MB model)...')
    from backend.services import curriculum

    idx = curriculum.get_index()
    print(f'  Topics: {len(idx.curriculum.topics)}   Chunks: {len(idx.all_chunks())}   Search backend: {idx.backend}')
    for question in ('What image does a concave mirror form?', 'Why does a heavier cart accelerate less?'):
        print(f'\n  Q: {question}')
        for hit in curriculum.search(question, k=3):
            print(f'    {hit.score:8.3f}  [{hit.chunk.topic_id}] {hit.chunk.text[:60]}...')
    if missing_opt:
        print(f'\nOptional and not installed: {", ".join(missing_opt)}. Everything else works.')
        print('  To add them: python -m pip install -r backend/requirements-rag.txt')
    else:
        print('\nEverything is installed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
