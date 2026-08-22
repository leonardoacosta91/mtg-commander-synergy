"""Frontend Streamlit de consulta de cartas (T-108).

Mini app web: se escribe el nombre exacto de una carta y se muestra su
ficha de jugador (imagen, costo de mana, tipo, poder/resistencia,
identidad de color y texto). Todo el HTTP pasa por el ``ScryfallClient``
del proyecto: nada de ``requests`` directo en la app.
"""

import re

import requests
import streamlit as st

from mtg_commander.extraction.client import ScryfallClient
from mtg_commander.ingestion.commander import ORDEN_WUBRG

ENDPOINT_NOMBRE = "/cards/named"
URL_SIMBOLO = "https://svgs.scryfall.io/card-symbols/{simbolo}.svg"

st.set_page_config(page_title="Consulta de cartas", page_icon="🃏")
st.title("🃏 Consulta de cartas")
st.caption("Escribí el nombre exacto de una carta y mirá su ficha de jugador.")


@st.cache_resource(show_spinner=False)
def obtener_client() -> ScryfallClient:
    """Crea el client de Scryfall una sola vez por sesión del servidor.

    Streamlit re-ejecuta el script entero ante cada interacción; con
    ``cache_resource`` todos los reruns comparten el mismo client (y su
    rate limiting), en vez de crear uno nuevo cada vez.

    Returns:
        ScryfallClient: cliente configurado con headers, retry y rate limit.
    """
    return ScryfallClient()


@st.cache_data(ttl=86400, show_spinner=False)
def buscar_carta(nombre: str) -> dict:
    """Resuelve una carta por nombre exacto contra /cards/named.

    Los resultados se cachean 24h (Scryfall recomienda cachear al menos un
    día: los datos de gameplay casi no cambian). El client inyecta rate
    limiting de 500ms y reintenta ante HTTP 429 automáticamente.

    Args:
        nombre (str): Nombre exacto de la carta a consultar.

    Returns:
        dict: Payload de la carta tal como lo devuelve Scryfall.

    Raises:
        ValueError: Si Scryfall no conoce la carta (HTTP 404).
        requests.HTTPError: Si la API falla por otra razón (ej. servidor).
    """
    client = obtener_client()
    try:
        return client.get(ENDPOINT_NOMBRE, params={"exact": nombre})
    except requests.HTTPError as error:
        respuesta = error.response
        if respuesta is not None and respuesta.status_code == 404:
            raise ValueError(f"No se encontró la carta: {nombre}") from error
        raise


def caras_de_carta(carta: dict) -> list[dict]:
    """Devuelve las caras mostrables de la carta.

    Para cartas de doble cara (MDFC, transform, split, adventure) devuelve
    ``card_faces``; para el resto, la propia carta como única cara. Así el
    resto del código siempre lee campos de una "cara", sin casos especiales.

    Args:
        carta (dict): Payload de Scryfall.

    Returns:
        list[dict]: Una o dos caras, cada una con name/mana_cost/etc.
    """
    caras = carta.get("card_faces") or []
    return caras if len(caras) >= 2 else [carta]


def url_imagen(objeto: dict) -> str | None:
    """Devuelve la URL de la imagen grande de una carta o de una cara suelta."""
    uris = objeto.get("image_uris") or {}
    return uris.get("png") or uris.get("normal")


def simbolos_html(tokens: list[str]) -> str:
    """Convierte una lista de símbolos de maná en imágenes HTML en línea.

    Args:
        tokens (list[str]): Símbolos sin llaves, ej. ["1", "W", "U", "B"] o
            híbridos como ["G/W"] (se mapean al archivo "GW.svg" de Scryfall).

    Returns:
        str: Etiquetas <img> listas para incrustar con unsafe_allow_html.
    """
    etiquetas = []
    for token in tokens:
        url = URL_SIMBOLO.format(simbolo=token.replace("/", ""))
        etiquetas.append(
            f'<img src="{url}" width="24" height="24" '
            f'style="vertical-align: middle; margin-right: 3px" alt="{{{token}}}">'
        )
    return "".join(etiquetas)


def tokens_mana(costo: str) -> list[str]:
    """Extrae los símbolos de un string de costo de maná de Scryfall.

    Args:
        costo (str): Costo con formato Scryfall, ej. "{1}{W}{U}{B}".

    Returns:
        list[str]: Tokens sin llaves, ej. ["1", "W", "U", "B"].
    """
    return re.findall(r"\{([^{}]+)\}", costo)


with st.form("busqueda"):
    nombre = st.text_input(
        "Nombre de la carta",
        placeholder="Y'shtola, Night's Blessed",
    )
    enviado = st.form_submit_button("Buscar", type="primary", use_container_width=True)

# El text_input recuerda su valor entre re-ejecuciones (estado interno del
# widget), así que basta con que haya texto para mostrar los resultados:
# al alternar lados el script se vuelve a correr y la carta sigue ahí.
if enviado and not nombre.strip():
    st.warning("Primero escribí el nombre de una carta.")
elif nombre.strip():
    try:
        carta = buscar_carta(nombre.strip())
    except ValueError as error:
        st.warning(f"No encontré esa carta. Revisá que esté bien escrita. ({error})")
    except requests.RequestException as error:
        st.error(f"Fallo la comunicación con Scryfall: {error}")
    else:
        caras = caras_de_carta(carta)
        indice = 0
        if len(caras) > 1:
            nombres_caras = [
                cara.get("name", f"Lado {i + 1}") for i, cara in enumerate(caras)
            ]
            # Botón flip estilo Archidekt: cada clic da vuelta la carta. La
            # etiqueta y la key son FIJAS: si la etiqueta cambiara según el
            # lado, Streamlit lo trataría como un widget nuevo en cada clic
            # y el clic quedaría registrado contra el widget anterior. Si se
            # busca otra carta, el índice vuelve a 0 (anverso).
            id_carta = carta.get("id")
            if st.session_state.get("carta_mostrada") != id_carta:
                st.session_state["carta_mostrada"] = id_carta
                st.session_state["lado_visible"] = 0

            if st.button("🔄", key="flip_lado"):
                st.session_state["lado_visible"] = (
                    st.session_state.get("lado_visible", 0) + 1
                ) % len(caras)
            indice = st.session_state.get("lado_visible", 0)
        cara_actual = caras[indice]

        columna_imagen, columna_datos = st.columns([1, 2])

        with columna_imagen:
            imagen = url_imagen(cara_actual)
            if imagen:
                st.image(imagen, use_container_width=True)

        with columna_datos:
            st.subheader(cara_actual.get("name", nombre))

            costo = cara_actual.get("mana_cost") or ""
            st.markdown(
                "**Costo de maná:** "
                + (simbolos_html(tokens_mana(costo)) or "—"),
                unsafe_allow_html=True,
            )

            st.text(f"Tipo: {cara_actual.get('type_line') or '—'}")

            identidad = sorted(
                carta.get("color_identity") or [], key=ORDEN_WUBRG.index
            )
            st.markdown(
                "**Identidad de color:** "
                + (simbolos_html(identidad) or "Incoloro"),
                unsafe_allow_html=True,
            )

            if cara_actual.get("power") is not None:
                st.text(
                    "Poder/Resistencia: "
                    f"{cara_actual['power']}/{cara_actual['toughness']}"
                )

            texto = cara_actual.get("oracle_text")
            if texto:
                st.markdown("**Texto de la carta**")
                # Cada símbolo {X} del oracle_text se reemplaza por su imagen.
                html_texto = re.sub(
                    r"\{([^{}]+)\}",
                    lambda coincidencia: simbolos_html([coincidencia.group(1)]),
                    texto,
                )
                st.markdown(html_texto.replace("\n", "<br>"), unsafe_allow_html=True)
else:
    st.info("Todavía no buscaste nada. Probá con una criatura conocida 😉")
