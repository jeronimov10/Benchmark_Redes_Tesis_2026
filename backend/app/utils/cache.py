"""Cache en memoria con TTL y desalojo LRU, segura para uso concurrente desde hilos y tareas asyncio."""

import threading
import time
from collections import OrderedDict


class CacheTTL:
    def __init__(self, max_entradas=500, ttl_s=None):
        self._datos = OrderedDict()
        self._max = max_entradas
        self._ttl = ttl_s
        self._lock = threading.Lock()
        self.aciertos = 0
        self.fallos = 0

    def obtener(self, clave):
        with self._lock:
            item = self._datos.get(clave)
            if item is None:
                self.fallos += 1
                return None
            valor, vence = item
            if vence is not None and vence < time.monotonic():
                del self._datos[clave]
                self.fallos += 1
                return None
            self._datos.move_to_end(clave)
            self.aciertos += 1
            return valor

    def guardar(self, clave, valor, ttl_s=None):
        ttl = ttl_s if ttl_s is not None else self._ttl
        vence = time.monotonic() + ttl if ttl is not None else None
        with self._lock:
            self._datos[clave] = (valor, vence)
            self._datos.move_to_end(clave)
            while len(self._datos) > self._max:
                self._datos.popitem(last=False)

    def invalidar(self, prefijo=None):
        with self._lock:
            if prefijo is None:
                self._datos.clear()
                return
            for k in [k for k in self._datos if isinstance(k, str) and k.startswith(prefijo)]:
                del self._datos[k]

    def __len__(self):
        with self._lock:
            return len(self._datos)
