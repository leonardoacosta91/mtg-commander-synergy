"""Tests de card_info: no golpean la red, mockean ScryfallClient.post."""

import unittest
from unittest.mock import MagicMock

from mtg_commander.context.card_info import obtener_info_cartas, partir_en_batches


class TestPartirEnBatches(unittest.TestCase):
    def test_lista_de_160_da_tres_batches(self):
        nombres = [f"Carta {i}" for i in range(160)]
        batches = partir_en_batches(nombres)

        self.assertEqual([len(b) for b in batches], [75, 75, 10])
        # La reconstrucción de los batches debe dar la lista original.
        self.assertEqual([n for b in batches for n in b], nombres)

    def test_lista_vacia_da_cero_batches(self):
        self.assertEqual(partir_en_batches([]), [])


class TestObtenerInfoCartas(unittest.TestCase):
    def test_normaliza_dedup_y_respeta_orden_original(self):
        cliente = MagicMock()
        cliente.post.return_value = {
            "data": [
                {
                    "name": "Sol Ring",
                    "oracle_text": "Add {C}{C}.",
                    "mana_cost": "{1}",
                    "type_line": "Artifact",
                    "colors": [],
                    "color_identity": [],
                    "rarity": "uncommon",
                    "prices": {"usd": "1.50"},  # campo que NO debe sobrevivir la normalización
                },
                {
                    "name": "Island",
                    "oracle_text": None,
                    "mana_cost": None,
                    "type_line": "Basic Land — Island",
                    "colors": [],
                    "color_identity": [],
                    "rarity": "common",
                },
            ],
            "not_found": [],
        }

        # "Island" repetida dos veces: no debe duplicar el pedido a Scryfall.
        nombres = ["Sol Ring", "Island", "Island"]
        resultado = obtener_info_cartas(cliente, nombres)

        cliente.post.assert_called_once()
        endpoint_llamado, body_llamado = cliente.post.call_args[0]
        self.assertEqual(endpoint_llamado, "/cards/collection")
        self.assertEqual(
            body_llamado["identifiers"], [{"name": "Sol Ring"}, {"name": "Island"}]
        )

        self.assertEqual(len(resultado), 3)  # respeta las 3 entradas de "nombres"
        self.assertEqual(resultado[0]["name"], "Sol Ring")
        self.assertNotIn("prices", resultado[0])
        self.assertEqual(resultado[1], resultado[2])  # ambas "Island" son iguales

    def test_carta_no_encontrada_no_crashea_y_se_excluye(self):
        cliente = MagicMock()
        cliente.post.return_value = {
            "data": [],
            "not_found": [{"name": "Carta Que No Existe"}],
        }

        resultado = obtener_info_cartas(cliente, ["Carta Que No Existe"])

        self.assertEqual(resultado, [])

    def test_mas_de_75_cartas_hace_dos_pedidos(self):
        cliente = MagicMock()
        cliente.post.side_effect = [
            {"data": [{"name": f"Carta {i}", "oracle_text": "", "mana_cost": "",
                       "type_line": "", "colors": [], "color_identity": [], "rarity": ""}
                      for i in range(75)], "not_found": []},
            {"data": [{"name": f"Carta {i}", "oracle_text": "", "mana_cost": "",
                       "type_line": "", "colors": [], "color_identity": [], "rarity": ""}
                      for i in range(75, 80)], "not_found": []},
        ]

        nombres = [f"Carta {i}" for i in range(80)]
        resultado = obtener_info_cartas(cliente, nombres)

        self.assertEqual(cliente.post.call_count, 2)
        self.assertEqual(len(resultado), 80)


if __name__ == "__main__":
    unittest.main()
