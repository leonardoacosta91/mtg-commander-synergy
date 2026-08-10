"""Cliente base para consumir la API de Scryfall.

Centraliza los requisitos obligatorios de la API: headers
User-Agent/Accept, rate limiting por endpoint y manejo de HTTP 429
con backoff exponencial.
"""

import logging
import time

import requests

class ScryfallClient:
    def __init__(
        self,
        base_url: str = "https://api.scryfall.com",
        user_agent: str = "MTGCommanderApp/1.0",
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
    ):
        self.base_url = base_url
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        self.headers = {
            "User-Agent": user_agent,
            "Accept": "application/json",
        }

        self.session = requests.Session()
        self.session.headers.update(self.headers)

        self.rate_limits = {
            "/cards/search": 0.5,
            "/cards/collection": 0.5,
            "/cards/named": 0.5,
            "/cards/random": 0.5,
            "default": 0.1,
        }

        self.last_request_time = 0.0

        self.logger = logging.getLogger(__name__)

    def _wait_if_needed(self, endpoint: str) -> None:
        """Espera lo necesario según el rate limit del endpoint antes de pedir."""
        delay = self.rate_limits.get(endpoint, self.rate_limits["default"])
        elapsed = time.time() - self.last_request_time
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self.last_request_time = time.time()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
    ) -> dict:
        """Hace el pedido HTTP, maneja 429 con retry/backoff, devuelve JSON."""
        url = f"{self.base_url}{endpoint}"

        for intento in range(1, self.max_retries + 1):
            self._wait_if_needed(endpoint)

            try:
                respuesta = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=self.timeout,
                )
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Error de conexión (intento {intento}): {e}")
                if intento == self.max_retries:
                    raise
                continue

            if respuesta.status_code == 429:
                if intento < self.max_retries:
                    espera = self.backoff_factor * (2 ** (intento - 1))
                    self.logger.warning(
                        f"429 recibido en {endpoint}, esperando {espera}s (intento {intento})"
                    )
                    time.sleep(espera)
                continue

            respuesta.raise_for_status()  # lanza excepción si es 4xx/5xx (no 429)
            return respuesta.json()

        raise RuntimeError(f"Se agotaron los reintentos ({self.max_retries}) para {endpoint}")

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        """Punto de entrada público: pide datos a Scryfall vía GET."""
        if not endpoint.startswith("/"):
            raise ValueError(f"El endpoint debe empezar con '/': {endpoint!r}")
        return self._request("GET", endpoint, params)

