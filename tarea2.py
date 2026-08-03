from datetime import datetime


def generar_nombre_csv(set_name="Decklist"):
    ahora = datetime.now()

    fecha_str = ahora.strftime("%Y%m%d")

    nombre_archivo = f"resultados_{set_name}_{fecha_str}.csv"

    return nombre_archivo

if __name__ == "__main__":
    nombre_generado = generar_nombre_csv("Decklist")

    print("Nombre de archivo generado:")
    print(nombre_generado)