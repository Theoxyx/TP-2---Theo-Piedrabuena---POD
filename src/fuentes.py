from abc import ABC, abstractmethod
import csv
import json
from pathlib import Path
import pandas as pd

class ErrorDatos(ValueError):
    """La entrada no cumple el contrato de la aplicación."""

class FuenteDatos(ABC):
    def __init__(self, ruta):
        self._ruta = Path(ruta)

    @property
    def ruta(self):
        return self._ruta

    def comprobar_archivo(self):
        if not self.ruta.is_file():
            raise FileNotFoundError(f'No existe el archivo: {self.ruta.name}')

    @abstractmethod
    def cargar(self):
        """Devuelve una tabla; puede fallar si el archivo es ilegible."""
        raise NotImplementedError

class FuenteCSV(FuenteDatos):
    def cargar(self):
        self.comprobar_archivo()
        return pd.read_csv(self.ruta)

class FuenteJSON(FuenteDatos):
    def cargar(self):
        self.comprobar_archivo()
        with self.ruta.open(encoding='utf-8') as archivo:
            contenido = json.load(archivo)
        if not isinstance(contenido, list) or not all(
            isinstance(fila, dict) for fila in contenido
        ):
            raise ErrorDatos('El JSON debe ser una lista de objetos (registros).')
        return pd.DataFrame(contenido)