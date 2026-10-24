from abc import ABC, abstractmethod
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
        try:
            return pd.read_csv(self.ruta, encoding='utf-8')
        except pd.errors.EmptyDataError as error:
            raise ErrorDatos(f'El CSV {self.ruta.name} está vacío.') from error
        except (pd.errors.ParserError, UnicodeDecodeError) as error:
            raise ErrorDatos(
                f'No se pudo leer el CSV {self.ruta.name}: {error}'
            ) from error

class FuenteJSON(FuenteDatos):
    def cargar(self):
        self.comprobar_archivo()
        try:
            with self.ruta.open(encoding='utf-8') as archivo:
                contenido = json.load(archivo)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ErrorDatos(
                f'No se pudo leer el JSON {self.ruta.name}: {error}'
            ) from error
        if not isinstance(contenido, list) or not all(
            isinstance(fila, dict) for fila in contenido
        ):
            raise ErrorDatos('El JSON debe ser una lista de objetos (registros).')
        return pd.DataFrame(contenido)
    
    
FUENTES_POR_EXTENSION = {
    '.csv': FuenteCSV,
    '.json': FuenteJSON,
}
 
 
def fuente_desde_ruta(ruta):
    """Elige la fuente adecuada según la extensión del archivo."""
    extension = Path(ruta).suffix.lower()
    if extension not in FUENTES_POR_EXTENSION:
        soportados = ', '.join(sorted(FUENTES_POR_EXTENSION))
        raise ErrorDatos(
            f"Formato '{extension or 'sin extensión'}' no soportado. "
            f'Formatos disponibles: {soportados}.'
        )
    return FUENTES_POR_EXTENSION[extension](ruta)