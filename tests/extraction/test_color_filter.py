"""Tests de color_filter.py: función pura, sin red ni cache."""

import unittest

from mtg_commander.extraction.color_filter import filtrar_por_identidad


def _carta(nombre: str, identidad: list[str]) -> dict:
    return {"name": nombre, "type_line": "Creature", "color_identity": identidad}


class TestFiltrarPorIdentidad(unittest.TestCase):
    def test_esper_solo_deja_pasar_wub_e_incoloras(self):
        # Criterio de aceptación del ticket T-203.
        mazo = [
            _carta("Swords to Plowshares", ["W"]),
            _carta("Solemn Simulacrum", []),
            _carta("Cyclonic Rift", ["U"]),
            _carta("Lightning Bolt", ["R"]),
            _carta("Giant Growth", ["G"]),
        ]

        resultado = filtrar_por_identidad(mazo, ["W", "U", "B"])

        self.assertEqual(
            [c["name"] for c in resultado],
            ["Swords to Plowshares", "Solemn Simulacrum", "Cyclonic Rift"],
        )

    def test_simbolos_del_texto_cuentan_en_ambas_caras(self):
        # Garruk Relentless: frente verde; el reverso tiene pips {B} en su
        # texto -> Scryfall le asigna identidad [G, B]. Crypt Ghast cuesta
        # solo negro pero su extort {W/B} lo hace [B, W].
        garruk = _carta("Garruk Relentless", ["G", "B"])
        cripta = _carta("Crypt Ghast", ["B", "W"])

        self.assertEqual(filtrar_por_identidad([garruk], ["G"]), [])
        self.assertEqual(filtrar_por_identidad([cripta], ["B"]), [])

    def test_comandante_incoloro_solo_acepta_cartas_sin_color(self):
        mazo = [_carta("Sol Ring", []), _carta("Counterspell", ["U"])]

        resultado = filtrar_por_identidad(mazo, [])

        self.assertEqual([c["name"] for c in resultado], ["Sol Ring"])

    def test_descarta_cartas_sin_campo_color_identity(self):
        sospechosa = {"name": "Carta Rara", "type_line": "Artifact"}
        ok = _carta("Sol Ring", [])

        resultado = filtrar_por_identidad([sospechosa, ok], ["W"])

        self.assertEqual([c["name"] for c in resultado], ["Sol Ring"])

    def test_normaliza_minusculas_y_conserva_orden(self):
        # La misma letra en minúscula debe pasar; el orden original se conserva.
        mazo = [
            _carta("Beta", ["w"]),
            _carta("Alfa", ["W"]),
        ]

        resultado = filtrar_por_identidad(mazo, ["W"])

        self.assertEqual([c["name"] for c in resultado], ["Beta", "Alfa"])


if __name__ == "__main__":
    unittest.main()
