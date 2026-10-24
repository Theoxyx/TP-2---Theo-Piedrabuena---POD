import re
import pandas as pd
import numpy as np
import math
import numbers

from src.dominio import BECAS, CONDICIONES, ReglasAcademicas
from src.fuentes import ErrorDatos

COLUMNAS_NOTAS = [
    'nota_matematica',
    'nota_programacion',
    'nota_estadistica',
    'nota_bases_datos',
    'nota_fisica',
]
COLUMNAS_REQUERIDAS = [
    'legajo',
    'nombre_estudiante',
    'carrera',
    *COLUMNAS_NOTAS,
    'asistencia_pct',
    'adeuda_correlativas',
]
COLUMNAS_REPORTE = [
    'legajo',
    'nombre_estudiante',
    'carrera',
    'promedio_final',
    'condicion_academica',
    'beca_merito',
]

PATRON_LEGAJO = re.compile(r'[0-9]{5}-[0-9]{1}')
ESCALA_LETRAS = {'A': 10.0, 'B+': 9.0, 'B': 8.0, 'C': 6.0, 'D': 4.0}
PATRON_PORCENTAJE = re.compile(r'(\d+(?:\.\d+)?)/100')
MARCAS_AUSENTE = {'', 'AUSENTE'}
 
 
class ErrorResultado(RuntimeError):
    """El resultado calculado no cumple las propiedades que debería tener."""
    
    
def legajo_valido(valor):
    """True si el legajo tiene el formato NNNNN-D y la base no es 00000."""
    if not isinstance(valor, str) or PATRON_LEGAJO.fullmatch(valor) is None:
        return False
    return int(valor[:5]) != 0


def normalizar_nota(valor):
    """Convierte una nota en escala mixta a número (escala 0-10).
 
    - Nulos y marcas de ausencia ('', 'Ausente') -> NaN (nota ausente).
    - Números -> float. Texto numérico, admitiendo coma decimal ('8,5').
    - Letras (A, B+, B, C, D) -> según ESCALA_LETRAS.
    - Porcentajes 'NN/100' -> NN / 10.
 
    No valida el rango: eso lo hace validar_y_limpiar_actas. Si el valor no
    se reconoce lanza ValueError, para no confundir "formato desconocido"
    con "estudiante ausente".
    """
    if valor is None or valor is pd.NA:
        return np.nan
    if isinstance(valor, (bool, np.bool_)):
        raise ValueError(f'un booleano no es una nota válida: {valor!r}')
    if isinstance(valor, numbers.Real):
        if math.isnan(valor):
            return np.nan
        if not math.isfinite(valor):
            raise ValueError(f'nota no finita: {valor!r}')
        return float(valor)
    if not isinstance(valor, str):
        raise ValueError(f'tipo de nota no soportado: {type(valor).__name__}')
 
    texto = valor.strip().upper().replace(',', '.')
    if texto in MARCAS_AUSENTE:
        return np.nan
    if texto in ESCALA_LETRAS:
        return ESCALA_LETRAS[texto]
    porcentaje = PATRON_PORCENTAJE.fullmatch(texto)
    if porcentaje:
        return float(porcentaje.group(1)) / 10.0
    try:
        numero = float(texto)
    except ValueError:
        raise ValueError(f'formato de nota no reconocido: {valor!r}') from None
    if not math.isfinite(numero):
        raise ValueError(f'formato de nota no reconocido: {valor!r}')
    return numero
 
 
def normalizar_booleano(valor):
    """Devuelve True/False, o None si el valor no es interpretable."""
    if isinstance(valor, (bool, np.bool_)):
        return bool(valor)
    if isinstance(valor, str):
        texto = valor.strip().lower()
        if texto == 'true':
            return True
        if texto == 'false':
            return False
        return None
    if isinstance(valor, numbers.Integral) and valor in (0, 1):
        return bool(valor)
    return None
 
    
def _exigir_columnas(df, columnas):
    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes:
        raise ErrorDatos(
            f"Faltan columnas obligatorias: {', '.join(faltantes)}. "
            f"Columnas recibidas: {', '.join(map(str, df.columns)) or '(ninguna)'}."
        )
            
            
def validar_esquema(df):
    """Comprueba que la tabla tenga todas las columnas que usa el análisis."""
    _exigir_columnas(df, COLUMNAS_REQUERIDAS)



def transformar_y_resumir(df_valido: pd.DataFrame):

    df_trabajo = df_valido.copy()
    
    materias = ['nota_matematica', 'nota_programacion', 'nota_estadistica', 'nota_bases_datos', 'nota_fisica']
    
    for m in materias:
        df_trabajo[m] = df_trabajo[m].apply(normalizar_nota)

    df_resultado = (
        df_trabajo
        .assign(
            ausentes_totales=lambda tabla: tabla[materias].isna().sum(axis=1),
            promedio_final=lambda tabla: tabla[materias].mean(axis=1).round(2),
            condicion_academica=lambda tabla: np.select(
                [
                    (tabla['ausentes_totales'] >= 3) & (tabla['asistencia_pct'] < 40),
                    (tabla['promedio_final'] >= 8.0) & (tabla['asistencia_pct'] >= 70) & (tabla['adeuda_correlativas'] == False),
                    (tabla['promedio_final'] >= 4.0) & (tabla['asistencia_pct'] >= 60)
                ],
                ['Abandono', 'Promocionado', 'Regular'],
                default='Libre'
            ),

            ranking_carrera=lambda tabla: tabla.groupby('carrera')['promedio_final'].rank(method='dense', ascending=False),
            beca_merito=lambda tabla: np.select(
                [
                    (tabla['promedio_final'] > 9.0) & (tabla['asistencia_pct'] >= 80) & (tabla['ranking_carrera'] == 1),
                    (tabla['promedio_final'] > 9.0) & (tabla['asistencia_pct'] >= 80) & (tabla['ranking_carrera'] > 1)
                ],
                ['Beca Completa', 'Beca Parcial'],
                default='Sin Beca'
            )
        )
    )

    return df_resultado