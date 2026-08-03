# Importamos las funciones que creaste en los otros archivos
from tarea1 import leer_decklist
from tarea2 import generar_nombre_csv


def ejecutar_procesamiento():
    print("=== INICIANDO PROCESO DE DECKLIST ===")

    # PASO 1: Leer el mazo local (.txt)
    archivo_entrada = "data/yshtola_esper.txt"
    cartas = leer_decklist(archivo_entrada)
    print(f"✓ Decklist leída correctamente ({len(cartas)} cartas encontradas).")

    # PASO 2: Generar el nombre para el reporte final (.csv)
    archivo_salida = generar_nombre_csv("Decklist")
    print(f"✓ Nombre de salida generado: {archivo_salida}")

    print("\n--- RESUMEN ---")
    print(f"Procesando cartas: {cartas}")
    print(f"Siguiente paso del proyecto: Guardar datos en -> {archivo_salida}")


if __name__ == "__main__":
    ejecutar_procesamiento()