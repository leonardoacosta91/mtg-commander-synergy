"""Research web del deck via Reddit API (PRAW).

Etapa 2b del flujo de Deck Context: busca en Reddit información sobre
el comandante del mazo (win conditions, sinergias, valoración de la
comunidad) y genera el archivo `research.md`.

El módulo solo recolecta y estructura texto crudo de Reddit. La síntesis
con LLM ocurre en la Etapa 2c (T-105).
"""

import logging
import os
import re
from datetime import date
from pathlib import Path

import praw
from dotenv import load_dotenv

from mtg_commander.context.deck_profiler import DeckProfile
from mtg_commander.ingestion.local import leer_decklist

logger = logging.getLogger(__name__)

# ── Constantes configurables ──────────────────────────────────────────────────
SUBREDDITS: list[str] = ["EDH", "CompetitiveEDH"]

# Queries enfocados en información estratégica; se buscan en orden y se deduplicán por ID.
QUERIES: list[str] = [
    "{commander} win conditions",
    "{commander} synergies deck",
    "{commander} how to win",
]
MAX_QUERIES_PERFIL = 3

MAX_POSTS: int = 3        # posts por query por subreddit
MAX_POSTS_TOTAL: int = 24  # límite global tras deduplicar y ordenar por score
MAX_COMMENTS: int = 3     # comentarios top por post
MAX_CHARS_POST: int = 1200  # caracteres máximos del selftext por post
MAX_CHARS_COMMENT: int = 800  # caracteres máximos por comentario

RESEARCH_MD_PATH = Path("research.md")


# ── Cliente Reddit ─────────────────────────────────────────────────────────────

class RedditClient:
    """Wrapper de praw.Reddit inicializado desde variables de entorno.

    Lee las credenciales del archivo .env (via python-dotenv) y expone
    una instancia de `praw.Reddit` lista para usar.

    Attributes:
        reddit (praw.Reddit): instancia autenticada de PRAW.
    """

    def __init__(self) -> None:
        load_dotenv()

        client_id = os.getenv("REDDIT_CLIENT_ID", "")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
        username = os.getenv("REDDIT_USERNAME", "")
        password = os.getenv("REDDIT_PASSWORD", "")
        user_agent = os.getenv("REDDIT_USER_AGENT", "")

        missing = [
            nombre
            for nombre, val in {
                "REDDIT_CLIENT_ID": client_id,
                "REDDIT_CLIENT_SECRET": client_secret,
                "REDDIT_USERNAME": username,
                "REDDIT_PASSWORD": password,
                "REDDIT_USER_AGENT": user_agent,
            }.items()
            if not val
        ]
        if missing:
            raise EnvironmentError(
                f"Faltan variables de entorno para Reddit: {', '.join(missing)}. "
                "Completá el archivo .env usando .env.example como referencia."
            )

        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=user_agent,
        )
        logger.info("RedditClient inicializado como u/%s", username)


# ── Búsqueda y extracción ─────────────────────────────────────────────────────

def _limpiar_texto(texto: str, max_chars: int) -> str:
    """Limpia whitespace y recorta el texto a `max_chars` caracteres.

    Args:
        texto (str): texto crudo (markdown de Reddit).
        max_chars (int): límite de caracteres de salida.

    Returns:
        str: texto limpio y recortado.
    """
    texto = re.sub(r"\n{3,}", "\n\n", texto.strip())
    if len(texto) > max_chars:
        texto = texto[:max_chars] + "… [recortado]"
    return texto


def _extraer_comentarios_top(submission: praw.models.Submission) -> list[str]:
    """Extrae los comentarios top de nivel raíz de un post.

    Args:
        submission (praw.models.Submission): post de Reddit.

    Returns:
        list[str]: lista de textos de comentarios limpios.
    """
    submission.comments.replace_more(limit=0)  # no expande "load more comments"
    comentarios: list[str] = []

    for comentario in submission.comments[:MAX_COMMENTS]:
        if not isinstance(comentario, praw.models.Comment):
            continue
        if comentario.body in ("[deleted]", "[removed]", ""):
            continue
        texto = _limpiar_texto(comentario.body, MAX_CHARS_COMMENT)
        comentarios.append(texto)

    return comentarios


def buscar_posts(
    client: RedditClient,
    commander: str,
    subreddits: list[str] = SUBREDDITS,
    queries: list[str] = QUERIES,
    limit: int = MAX_POSTS,
) -> list[dict]:
    """Busca posts sobre el comandante usando múltiples queries estratégicos.

    Itera sobre cada combinación (subreddit × query) y deduplica por submission ID
    para evitar repetir el mismo post si aparece en más de un query.

    Args:
        client (RedditClient): cliente autenticado.
        commander (str): nombre del comandante, ej. "Y'shtola, Night's Blessed".
        subreddits (list[str]): lista de subreddits donde buscar.
        queries (list[str]): templates de query con placeholder ``{commander}``.
        limit (int): máximo de posts por query por subreddit.

    Returns:
        list[dict]: lista de dicts con keys:
            - ``title`` (str): título del post.
            - ``url`` (str): URL del post en Reddit.
            - ``score`` (int): votos del post.
            - ``num_comments`` (int): cantidad de comentarios.
            - ``selftext`` (str): cuerpo del post limpio y recortado.
            - ``top_comments`` (list[str]): comentarios top limpios.
            - ``subreddit`` (str): nombre del subreddit.
    """
    vistos: set[str] = set()  # IDs de submissions ya procesados (dedup)
    posts: list[dict] = []

    for subreddit_name in subreddits:
        for query_template in queries:
            query = query_template.format(commander=commander)
            logger.info("Buscando en r/%s: %r", subreddit_name, query)
            try:
                subreddit = client.reddit.subreddit(subreddit_name)
                resultados = subreddit.search(query, sort="relevance", limit=limit)

                for submission in resultados:
                    if submission.id in vistos:
                        logger.debug("  Duplicado ignorado: %s", submission.title[:60])
                        continue
                    vistos.add(submission.id)

                    selftext = _limpiar_texto(submission.selftext or "", MAX_CHARS_POST)
                    comentarios = _extraer_comentarios_top(submission)

                    posts.append({
                        "title": submission.title,
                        "url": f"https://www.reddit.com{submission.permalink}",
                        "score": submission.score,
                        "num_comments": submission.num_comments,
                        "selftext": selftext,
                        "top_comments": comentarios,
                        "subreddit": subreddit_name,
                        "query": query,
                    })
                    logger.debug("  Post añadido: %s [%d↑]", submission.title[:60], submission.score)

            except Exception as exc:
                logger.warning("Error buscando en r/%s con query %r: %s", subreddit_name, query, exc)

    posts_ordenados = sorted(posts, key=lambda post: post["score"], reverse=True)
    seleccionados = posts_ordenados[:MAX_POSTS_TOTAL]
    logger.info("Posts recolectados: %d; seleccionados: %d", len(posts), len(seleccionados))
    return seleccionados


def construir_queries(commander: str, profile: DeckProfile | None = None) -> list[str]:
    """Construye queries generales y, opcionalmente, derivadas del deck.

    Args:
        commander: nombre del comandante del mazo.
        profile: tags inferidos de las cartas enriquecidas.

    Returns:
        Lista ordenada, deduplicada y acotada de queries para Reddit.
    """
    queries = [template.format(commander=commander) for template in QUERIES]
    if profile is not None:
        for tag in [*profile.archetypes, *profile.themes]:
            queries.append(f"{commander} {tag}")

    resultado: list[str] = []
    for query in queries:
        normalizada = " ".join(query.split())
        if normalizada and normalizada not in resultado:
            resultado.append(normalizada)
    return resultado[: len(QUERIES) + MAX_QUERIES_PERFIL]


# ── Construcción de research.md ───────────────────────────────────────────────

def _formatear_fuentes(posts: list[dict]) -> str:
    """Genera la tabla de fuentes en formato markdown.

    Args:
        posts (list[dict]): lista de posts recolectados.

    Returns:
        str: tabla markdown con columnas #, Fuente, Tipo, URL.
    """
    filas = ["| # | Fuente | Query | Tipo | URL |", "|---|--------|-------|------|-----|"]
    for i, post in enumerate(posts, start=1):
        nombre = post["title"][:60].replace("|", "-")
        filas.append(
            f"| {i} | {nombre} | {post.get('query', '—')} | hilo reddit (r/{post['subreddit']}) | {post['url']} |"
        )
    return "\n".join(filas)


def _formatear_contenido_posts(posts: list[dict]) -> str:
    """Serializa el contenido crudo de los posts para las secciones de research.

    Args:
        posts (list[dict]): lista de posts recolectados.

    Returns:
        str: texto consolidado listo para pegar en research.md.
    """
    bloques: list[str] = []
    for i, post in enumerate(posts, start=1):
        bloque = [
            f"### [F{i}] {post['title']} [{post['score']}↑ · r/{post['subreddit']}]",
            f"URL: {post['url']}\n",
        ]

        if post["selftext"]:
            bloque.append(post["selftext"])

        if post["top_comments"]:
            bloque.append("\n**Comentarios top:**")
            for j, comentario in enumerate(post["top_comments"], start=1):
                bloque.append(f"{j}. {comentario}")

        bloques.append("\n".join(bloque))

    return "\n\n---\n\n".join(bloques)


def construir_research_md(
    commander: str,
    color_identity: list[str],
    decklist_path: str,
    posts: list[dict],
    profile: DeckProfile | None = None,
) -> str:
    """Renderiza el contenido de research.md con los datos recolectados.

    Sigue el contrato de `mtg_commander/context/research_template.md`:
    fuentes trazables [F#], cartas entre [Carta], foco en el rol estratégico.

    Args:
        commander (str): nombre del comandante.
        color_identity (list[str]): identidad de color, ej. ["W", "U", "B"].
        decklist_path (str): ruta al archivo .txt del decklist.
        posts (list[dict]): posts recolectados por `buscar_posts()`.
        profile (DeckProfile | None): perfil automático que orientó las queries.

    Returns:
        str: contenido completo de research.md listo para escribir a disco.
    """
    color_str = "/".join(color_identity) if color_identity else "desconocida"
    hoy = date.today().isoformat()
    tabla_fuentes = _formatear_fuentes(posts)
    contenido_posts = _formatear_contenido_posts(posts)
    n_entradas = _contar_entradas_normalizadas(decklist_path)
    perfil = (
        f"- Arquetipos inferidos: {', '.join(profile.archetypes)}\n"
        f"- Mecánicas inferidas: {', '.join(profile.themes)}\n"
        f"- Resumen automático: {profile.summary}"
        if profile is not None
        else "- Perfil automático: no disponible (research general por comandante)."
    )

    return f"""# Research — {commander}

## Metadata

- Comandante: {commander}
- Color identity: {color_str}
- Decklist: {decklist_path} · {n_entradas} entradas normalizadas
- Fecha: {hoy}
{perfil}

## Fuentes consultadas

{tabla_fuentes}

> Regla de lectura: cada afirmación de las secciones siguientes referencia su fuente con `[F#]`
> para mantener la trazabilidad. Todo nombre de carta se escribe entre corchetes, ej. `[Exsanguinate]`,
> para que las etapas del LLM puedan resolver la carta concreta. Los paquetes/patrones descritos en
> "Sinergias y paquetes clave" se leen para **buscar coincidencias con cartas nuevas**: importa el
> *patrón de interacción* (qué habilidad del comandante desbloquea, con qué otras cartas opera),
> no la carta en sí como objeto aislado.

## Contenido recolectado de Reddit

> **Nota:** esta sección contiene el texto crudo de los posts más relevantes.
> Las secciones de Arquetipo, Win conditions y Sinergias se completan en T-105
> (LLM Pass 1) usando este material como fuente.

{contenido_posts}

## Arquetipo y perfil (consenso comunidad)

- Arquetipo: > TODO (T-105): sintetizar desde el contenido anterior con LLM.
- Nivel de poder: > TODO (T-105): sintetizar desde el contenido anterior con LLM.
- Posicionamiento en el metagame: > TODO (T-105): sintetizar desde el contenido anterior con LLM.

## Perfil de mana (curva observada)

- CMC promedio estimado: > TODO (T-105): sintetizar desde el contenido anterior con LLM.
- Foco del rango bajo (≤2 CMC): > TODO (T-105): sintetizar desde el contenido anterior con LLM.
- Cómo describe la comunidad la curva del mazo: > TODO (T-105): sintetizar desde el contenido anterior con LLM.

## Win conditions

> TODO (T-105): sintetizar desde el contenido anterior con LLM.

## Sinergias y paquetes clave

> TODO (T-105): sintetizar desde el contenido anterior con LLM.

## Cartas frecuentemente excluidas / debatidas

> TODO (T-105): sintetizar desde el contenido anterior con LLM.

## Contradicciones / dudas abiertas

> TODO (T-105): sintetizar desde el contenido anterior con LLM.
"""


def _contar_entradas_normalizadas(decklist_path: str) -> int:
    """Cuenta las entradas que el pipeline realmente procesa del decklist.

    Args:
        decklist_path (str): ruta al archivo .txt del decklist.

    Returns:
        int: número de nombres normalizados, o 0 si el archivo no existe.
    """
    try:
        return len(leer_decklist(decklist_path))
    except FileNotFoundError:
        return 0


# ── Función orquestadora pública ──────────────────────────────────────────────

def generar_research(
    commander: str,
    color_identity: list[str],
    decklist_path: str,
    output_path: Path = RESEARCH_MD_PATH,
    profile: DeckProfile | None = None,
) -> Path:
    """Recolecta información de Reddit y genera research.md.

    Función pública de la etapa 2b. Orquesta: autenticación → búsqueda →
    construcción del markdown → escritura a disco.

    Args:
        commander (str): nombre del comandante, ej. "Y'shtola, Night's Blessed".
        color_identity (list[str]): identidad de color del mazo, ej. ["W", "U", "B"].
        decklist_path (str): ruta al archivo .txt del decklist.
        output_path (Path): ruta de salida para research.md. Por defecto: ``research.md``
            en el directorio de trabajo actual.
        profile (DeckProfile | None): perfil de deck que genera queries específicas.

    Returns:
        Path: ruta absoluta al archivo research.md generado.

    Raises:
        EnvironmentError: si faltan variables de entorno para Reddit.
        praw.exceptions.PRAWException: si PRAW no puede autenticarse.
    """
    logger.info("Iniciando research para comandante: %s", commander)

    client = RedditClient()
    queries = construir_queries(commander, profile)
    logger.info("Queries de research: %s", queries)
    posts = buscar_posts(client, commander, queries=queries)

    if not posts:
        logger.warning(
            "No se encontraron posts para '%s'. research.md estará vacío.", commander
        )

    contenido = construir_research_md(
        commander, color_identity, decklist_path, posts, profile
    )

    output_path.write_text(contenido, encoding="utf-8")
    logger.info("research.md generado en: %s", output_path.resolve())

    return output_path.resolve()
