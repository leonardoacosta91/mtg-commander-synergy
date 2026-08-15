"""
Script de verificación de credenciales PRAW.
Uso: .venv/bin/python scripts/verify_reddit_auth.py

NO commitear este archivo con credenciales hardcodeadas.
Las credenciales se leen desde .env (excluido en .gitignore).
"""

import os
import sys

import praw
from dotenv import load_dotenv

load_dotenv()


def verify_reddit_credentials() -> None:
    """Verifica que las credenciales de Reddit en .env sean válidas."""
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    username = os.getenv("REDDIT_USERNAME")
    password = os.getenv("REDDIT_PASSWORD")
    user_agent = os.getenv("REDDIT_USER_AGENT")

    # Validar que todas las variables estén presentes
    missing = [
        name
        for name, val in {
            "REDDIT_CLIENT_ID": client_id,
            "REDDIT_CLIENT_SECRET": client_secret,
            "REDDIT_USERNAME": username,
            "REDDIT_PASSWORD": password,
            "REDDIT_USER_AGENT": user_agent,
        }.items()
        if not val or val.endswith("_here")
    ]

    if missing:
        print(f"[ERROR] Faltan variables en .env: {', '.join(missing)}")
        print("        Completá .env usando .env.example como referencia.")
        sys.exit(1)

    print("→ Variables de entorno: OK")
    print(f"  client_id  : {client_id[:6]}{'*' * (len(client_id) - 6)}")
    print(f"  username   : {username}")
    print(f"  user_agent : {user_agent}")
    print()

    # Intentar autenticación
    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=user_agent,
        )

        me = reddit.user.me()
        print(f"✅ Autenticado correctamente como: u/{me.name}")
        print(f"   Karma: {me.link_karma} (posts) / {me.comment_karma} (comentarios)")

    except Exception as e:
        print(f"❌ Error de autenticación: {type(e).__name__}: {e}")
        print()
        print("Causas comunes:")
        print("  401 → client_id o client_secret incorrectos")
        print("  403 → app deshabilitada o requiere re-aprobación en Reddit")
        print("  OAuthException → username/password incorrectos o 2FA activo")
        sys.exit(1)

    # Prueba real: buscar hilos de Commander
    print()
    print("→ Probando búsqueda en r/EDH...")
    try:
        subreddit = reddit.subreddit("EDH")
        resultados = list(subreddit.search("Y'shtola commander", sort="relevance", limit=3))

        if not resultados:
            print("⚠️  Búsqueda exitosa pero sin resultados para el query de prueba.")
        else:
            print(f"✅ Búsqueda OK — {len(resultados)} resultado(s) encontrado(s):\n")
            for post in resultados:
                print(f"  • [{post.score}↑] {post.title[:80]}")
                print(f"    Comentarios: {post.num_comments} | url: {post.url[:60]}")

    except Exception as e:
        print(f"❌ Error en búsqueda: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    verify_reddit_credentials()
