# Importamos las funciones de los módulos del pipeline
from collections import Counter

from mtg_commander.ingestion.local import leer_decklist
from tarea2 import generar_nombre_csv


def ejecutar_procesamiento():
    print("=== INICIANDO PROCESO DE DECKLIST ===")

    # PASO 1: Leer el mazo local (.txt)
    archivo_entrada = "data/yshtola_esper.txt"
    cartas = leer_decklist(archivo_entrada)
    print("OK: Decklist leída correctamente (" + str(len(cartas)) + " cartas encontradas).")

    # Advertencia si hay cartas repetidas
    conteo = Counter(cartas)
    repetidas = sorted(carta for carta, cantidad in conteo.items() if cantidad > 1)
    if repetidas:
        print("¡ADVERTENCIA! SE ENCONTRARON CARTAS REPETIDAS EN LA LISTA:")
        for carta in repetidas:
            print(f"  - {carta.upper()}")

    # PASO 2: Generar el nombre para el reporte final (.csv)
    archivo_salida = generar_nombre_csv("Decklist")
    print("OK: Nombre de salida generado: " + archivo_salida)

    print("\n--- RESUMEN ---")
    print(f"Procesando cartas: {cartas}")
    print(f"Siguiente paso del proyecto: Guardar datos en -> {archivo_salida}")


if __name__ == "__main__":
    ejecutar_procesamiento()