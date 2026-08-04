"""Ingesta de decklists desde archivos locales (.txt).

Implementa la V1 de la Etapa 1 del pipeline: lectura y normalización
de un decklist exportado desde Moxfield/Archidekt en texto plano.
"""

import os

SECCIONES_INCLUIDAS = {"Commander", "Deck"}
SECCIONES_EXCLUIDAS = {"Sideboard", "Maybeboard"}


def es_encabezado_seccion(linea: str) -> bool:
    """Determina si una línea corresponde a un encabezado de sección.

    Args:
        linea (str): Línea ya limpia (sin espacios ni saltos).

    Returns:
        bool: ``True`` si la línea es un encabezado conocido del decklist.
    """
    return linea in SECCIONES_INCLUIDAS | SECCIONES_EXCLUIDAS


def leer_comandante(ruta_archivo: str) -> str:
    """Lee la sección Commander y devuelve el nombre del comandante.

    Args:
        ruta_archivo (str): Ruta al decklist .txt.

    Returns:
        str: Nombre del comandante.

    Raises:
        FileNotFoundError: Si la ruta indicada no existe.
        ValueError: Si el decklist no tiene sección Commander.
    """
    if not os.path.exists(ruta_archivo):
        raise FileNotFoundError(f"No se encontró el decklist: {ruta_archivo}")

    with open(ruta_archivo, "r", encoding="utf-8") as archivo:
        en_comander = False
        for linea in archivo:
            linea_limpia = linea.strip()
            if not linea_limpia:
                continue

            # Un encabezado cambia la sección vigente.
            if es_encabezado_seccion(linea_limpia):
                en_comander = linea_limpia == "Commander"
                continue

            # La primera carta con cantidad en la sección Commander es el comandante.
            if en_comander:
                partes = linea_limpia.split(" ", 1)
                if partes[0].isdigit() and len(partes) > 1:
                    return partes[1]

    raise ValueError("El decklist no tiene un comandante en la sección Commander")


def leer_decklist(ruta_archivo: str) -> list[str]:
    """Lee un decklist .txt y devuelve los nombres normalizados de las cartas.

    Se procesan únicamente las secciones ``Commander`` y ``Deck``.
    Las secciones ``Sideboard`` y ``Maybeboard`` se descartan por no
    pertenecer al mazo principal.

    Args:
        ruta_archivo (str): Ruta al archivo de texto con el decklist.

    Returns:
        list[str]: Nombres de cartas sin cantidades ni encabezados.

    Raises:
        FileNotFoundError: Si la ruta indicada no existe.
    """
    if not os.path.exists(ruta_archivo):
        raise FileNotFoundError(f"No se encontró el decklist: {ruta_archivo}")

    cartas: list[str] = []
    # Por defecto se procesa todo (soporta archivos sin encabezados).
    seccion_activa = True

    with open(ruta_archivo, "r", encoding="utf-8") as archivo:
        for linea in archivo:
            linea_limpia = linea.strip()

            # Se saltean líneas vacías (reglones en blanco del archivo).
            if not linea_limpia:
                continue

            # Un encabezado cambia la sección vigente.
            if es_encabezado_seccion(linea_limpia):
                seccion_activa = linea_limpia in SECCIONES_INCLUIDAS
                continue

            # Las cartas fuera de secciones válidas se descartan.
            if not seccion_activa:
                continue

            # Se separa en el PRIMER espacio: [cantidad, nombre].
            partes = linea_limpia.split(" ", 1)

            # Solo interesan líneas con cantidad al inicio (ej. "1 Carta").
            if partes[0].isdigit() and len(partes) > 1:
                cartas.append(partes[1])

    return cartas
