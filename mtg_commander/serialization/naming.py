"""Generación de nombres de archivo para los reportes CSV del pipeline.

Implementa el T-003 del backlog: nombres únicos por timestamp completo
y almacenamiento centralizado en la carpeta ``outputs/``.
"""

import os
import uuid
from datetime import datetime

CARPETA_SALIDA = "outputs"


def generar_nombre_csv(set_name: str = "Decklist") -> str:
    """Genera la ruta de un archivo CSV único dentro de ``outputs/``.

    Combina un timestamp legible (fecha, hora, minutos y segundos) con
    un sufijo aleatorio corto, para que dos corridas del pipeline nunca
    se pisen entre sí. El sufijo es necesario porque el timestamp solo
    aporta contexto humano (para ordenar/ubicar el archivo): la
    resolución del reloj del sistema no alcanza para garantizar
    unicidad si el pipeline se corre dos veces muy seguido (en Windows
    puede devolver el mismo valor en llamadas consecutivas). Si la
    carpeta ``outputs/`` no existe, se crea.

    Args:
        set_name (str): Nombre descriptivo a incluir en el archivo
            (ej. nombre del mazo o del set evaluado).

    Returns:
        str: Ruta relativa del archivo CSV a generar, dentro de ``outputs/``.
    """
    os.makedirs(CARPETA_SALIDA, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sufijo_unico = uuid.uuid4().hex[:8]
    nombre_archivo = f"evaluation_{set_name}_{timestamp}_{sufijo_unico}.csv"

    return os.path.join(CARPETA_SALIDA, nombre_archivo)
