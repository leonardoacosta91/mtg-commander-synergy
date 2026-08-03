def leer_decklist(ruta_archivo):
    cartas_limpias = []

    # Abrimos el archivo .txt en modo lectura ("r")
    with open(ruta_archivo, "r", encoding="utf-8") as archivo:
        for linea in archivo:
            # Quitamos saltos de línea (\n) y espacios a los costados
            linea_limpia = linea.strip()

            # Si la línea está vacía (ej. reglón en blanco), nos la saltamos
            if not linea_limpia:
                continue

            # Separamos en el PRIMER espacio nada más
            partes = linea_limpia.split(" ", 1)

            # Solo contamos líneas que empiecen con una cantidad (ej. "1 Carta")
            # Los encabezados de sección ("Commander", "Deck", "Sideboard")
            # se ignoran porque no empiezan con un número
            if partes[0].isdigit() and len(partes) > 1:
                cartas_limpias.append(partes[1])

    # Detectamos cartas repetidas y avisamos al usuario
    repetidas = sorted({carta for carta in cartas_limpias if cartas_limpias.count(carta) > 1})
    if repetidas:
        print("¡ADVERTENCIA! SE ENCONTRARON CARTAS REPETIDAS EN LA LISTA:")
        for carta in repetidas:
            print(f"  - {carta.upper()}")

    return cartas_limpias


# --- PRUEBA DEL SCRIPT ---
# Llamamos a la función pasándole nuestro archivo
resultado = leer_decklist("data/yshtola_esper.txt")

# Imprimimos en pantalla para ver qué procesó
print("Lista de cartas procesada:")
print(resultado)