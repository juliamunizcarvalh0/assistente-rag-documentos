"""Publica o app como um Hugging Face Space (SDK Docker).

Monta uma pasta só com o que o app precisa (app.py, src/, leis/,
requirements.txt) mais o README e o Dockerfile de ``space/`` e envia ao Space
``<usuario>/pergunte-a-lei``, criando-o na primeira vez.

Variáveis de ambiente:
    HF_TOKEN        token do Hugging Face com permissão de escrita (obrigatório)
    GEMINI_API_KEY  se definida, vira um segredo do Space para ativar a IA
    HF_SPACE_NAME   nome do Space (padrão: pergunte-a-lei)

Uso:
    python scripts/deploy_hf_space.py            # publica
    python scripts/deploy_hf_space.py --dry-run  # só monta a pasta e lista
"""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_FILES = ["app.py", "requirements.txt", "LICENSE"]
APP_DIRS = ["src", "leis"]
SPACE_FILES = ["README.md", "Dockerfile"]


def build(dest: Path) -> list[str]:
    """Copia os arquivos do Space para ``dest`` e devolve a lista enviada."""
    for name in APP_FILES:
        shutil.copy2(ROOT / name, dest / name)
    for name in APP_DIRS:
        shutil.copytree(ROOT / name, dest / name,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in SPACE_FILES:
        shutil.copy2(ROOT / "space" / name, dest / name)
    return sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        files = build(Path(tmp))
        print(f"{len(files)} arquivos no Space")
        if args.dry_run:
            print("\n".join(files))
            return

        from huggingface_hub import HfApi

        token = os.environ.get("HF_TOKEN")
        if not token:
            raise SystemExit("Defina HF_TOKEN (token do Hugging Face com permissão de escrita).")
        api = HfApi(token=token)
        user = api.whoami()["name"]
        repo_id = f"{user}/{os.environ.get('HF_SPACE_NAME', 'pergunte-a-lei')}"

        api.create_repo(repo_id, repo_type="space", space_sdk="docker", exist_ok=True)
        if os.environ.get("GEMINI_API_KEY"):
            api.add_space_secret(repo_id, "GEMINI_API_KEY", os.environ["GEMINI_API_KEY"],
                                 description="Chave do Gemini para as respostas com IA")
            print("Segredo GEMINI_API_KEY configurado no Space.")
        sha = os.environ.get("GITHUB_SHA", "local")[:7]
        api.upload_folder(
            repo_id=repo_id,
            repo_type="space",
            folder_path=tmp,
            commit_message=f"Deploy a partir do GitHub ({sha})",
            delete_patterns=["src/**", "leis/**"],  # remove arquivos que saíram do repositório
        )
        print(f"Publicado: https://huggingface.co/spaces/{repo_id}")


if __name__ == "__main__":
    main()
