"""Generación de nombres de archivo para los reportes CSV del pipeline.

Implementa el T-003 del backlog: nombres únicos por timestamp completo
y almacenamiento centralizado en la carpeta ``outputs/``.
"""

import os
from datetime import datetime

CARPETA_SALIDA = "outputs"


def generar_nombre_csv(set_name: str = "Decklist") -> str:
    """Genera la ruta de un archivo CSV único dentro de ``outputs/``.

    Usa un timestamp completo (fecha, hora, minutos y segundos) para que
    dos corridas del pipeline nunca se pisen entre sí, incluso si se
    ejecutan el mismo día. Si la carpeta ``outputs/`` no existe, se crea.

    Args:
        set_name (str): Nombre descriptivo a incluir en el archivo
            (ej. nombre del mazo o del set evaluado).

    Returns:
        str: Ruta relativa del archivo CSV a generar, dentro de ``outputs/``.
    """
    os.makedirs(CARPETA_SALIDA, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"evaluation_{set_name}_{timestamp}.csv"

    return os.path.join(CARPETA_SALIDA, nombre_archivo)
