"""Serialización de la evaluación de sinergia del LLM (T-301) a CSV.

Etapa 5 del pipeline: convierte la lista de evaluaciones JSON (una por
carta, contrato definido en `data/evaluation_mock.json`) en un CSV
legible en Excel/Sheets, reutilizando el generador de nombres únicos
de T-003 (`naming.py`) para no pisar corridas anteriores.
"""

import csv
import json
import logging

from mtg_commander.serialization.naming import generar_nombre_csv

CAMPOS_CSV = (
    "card_name",
    "include",
    "recommendation_tier",
    "synergy_score",
    "synergy_category",
    "synergy_themes",
    "pros",
    "cons",
    "rationale",
)
CAMPOS_LISTA = ("synergy_themes", "pros", "cons")
SEPARADOR_LISTA = "; "

logger = logging.getLogger(__name__)


def cargar_evaluaciones(ruta_json: str) -> list[dict]:
    """Lee el JSON de evaluaciones del LLM (una entrada por carta).

    Args:
        ruta_json (str): ruta al archivo JSON (ej. el mock de T-301
            en `data/evaluation_mock.json`, o el output real una vez
            que T-301 esté implementado).

    Returns:
        list[dict]: entradas crudas, sin validar todavía.

    Raises:
        json.JSONDecodeError: si el archivo no es JSON válido.
        FileNotFoundError: si la ruta no existe.
    """
    with open(ruta_json, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def _fila_valida(evaluacion: dict) -> bool:
    """Una fila es válida si tiene todos los campos del contrato de T-301."""
    return all(campo in evaluacion for campo in CAMPOS_CSV)


def _serializar_fila(evaluacion: dict) -> dict:
    """Convierte una evaluación al formato de fila CSV (listas -> texto plano)."""
    fila = dict(evaluacion)
    for campo in CAMPOS_LISTA:
        valor = fila.get(campo, [])
        fila[campo] = SEPARADOR_LISTA.join(valor) if isinstance(valor, list) else valor
    return fila


def exportar_evaluacion_csv(evaluaciones: list[dict], set_name: str = "Decklist") -> str:
    """Exporta la lista de evaluaciones a un CSV único dentro de `outputs/`.

    Las filas a las que les falta algún campo del contrato no crashean
    la exportación: se registran como inválidas (log warning) y se
    excluyen del CSV, pero el resto de las filas válidas sí se
    exportan igual.

    Args:
        evaluaciones (list[dict]): evaluaciones ya parseadas (ver
            `cargar_evaluaciones`), una por carta.
        set_name (str): nombre descriptivo para el archivo de salida
            (se pasa a `generar_nombre_csv`).

    Returns:
        str: ruta del CSV generado.
    """
    ruta_csv = generar_nombre_csv(set_name)

    filas_validas = []
    for evaluacion in evaluaciones:
        if not _fila_valida(evaluacion):
            faltantes = [campo for campo in CAMPOS_CSV if campo not in evaluacion]
            logger.warning(
                "Fila inválida (faltan campos %s): %s",
                faltantes,
                evaluacion.get("card_name", "<sin nombre>"),
            )
            continue
        filas_validas.append(_serializar_fila(evaluacion))

    with open(ruta_csv, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=CAMPOS_CSV)
        escritor.writeheader()
        escritor.writerows(filas_validas)

    return ruta_csv
