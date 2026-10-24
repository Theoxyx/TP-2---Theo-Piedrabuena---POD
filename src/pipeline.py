import re
import pandas as pd
import numpy as np
import math
import numbers
from pathlib import Path

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

    if not isinstance(valor, str) or PATRON_LEGAJO.fullmatch(valor) is None:
        return False
    return int(valor[:5]) != 0


def normalizar_nota(valor):

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


def _marcar(motivos, mascara_error, texto):
    for posicion in np.flatnonzero(np.asarray(mascara_error, dtype=bool)):
        motivos[posicion].append(texto)
 
 
def _normalizar_columna_notas(serie, reglas):

    valores, errores = [], {}
    for posicion, original in enumerate(serie):
        try:
            nota = normalizar_nota(original)
        except ValueError as error:
            valores.append(np.nan)
            errores[posicion] = str(error)
            continue
        if not np.isnan(nota) and not reglas.nota_en_rango(nota):
            errores[posicion] = (
                f'nota fuera de rango '
                f'({reglas.nota_min:g}-{reglas.nota_max:g}): {original}'
            )
        valores.append(nota)
    return pd.Series(valores, index=serie.index, dtype=float), errores
 
 
def validar_y_limpiar_actas(df, reglas=None):
    
    reglas = reglas if reglas is not None else ReglasAcademicas()
    validar_esquema(df)
 
    original = df.reset_index(drop=True)
    trabajo = original.copy()
    motivos = [[] for _ in range(len(trabajo))]
 

    mascara_legajo = trabajo['legajo'].apply(legajo_valido).astype(bool)
    _marcar(motivos, ~mascara_legajo, 'Legajo malformado o inválido')
    repetido = (
        trabajo['legajo'].where(mascara_legajo).duplicated(keep='first')
        & mascara_legajo
    )
    _marcar(motivos, repetido, 'Legajo duplicado (se conserva la primera aparición)')
 
    # Asistencia: numérica y dentro de rango
    asistencia = pd.to_numeric(trabajo['asistencia_pct'], errors='coerce')
    _marcar(motivos, asistencia.isna(), 'Asistencia ausente o no numérica')
    fuera = asistencia.notna() & ~asistencia.between(
        reglas.asistencia_min, reglas.asistencia_max
    )
    _marcar(
        motivos,
        fuera,
        f'Asistencia fuera de rango ({reglas.asistencia_min:g}-{reglas.asistencia_max:g})',
    )
    trabajo['asistencia_pct'] = asistencia
 

    for columna in COLUMNAS_NOTAS:
        notas, errores = _normalizar_columna_notas(trabajo[columna], reglas)
        trabajo[columna] = notas
        for posicion, texto in errores.items():
            motivos[posicion].append(f'{columna}: {texto}')
 
    # Correlativas: valor booleano interpretable
    adeuda = trabajo['adeuda_correlativas'].apply(normalizar_booleano)
    _marcar(motivos, adeuda.isna(), 'adeuda_correlativas no es un valor booleano')
    trabajo['adeuda_correlativas'] = adeuda
 
    rechazada = np.array([bool(m) for m in motivos], dtype=bool)
 
    df_rechazados = original.loc[rechazada].copy()
    df_rechazados.insert(0, 'fila_origen', df_rechazados.index + 1)
    df_rechazados['motivo_rechazo'] = [
        '; '.join(motivos[posicion]) for posicion in df_rechazados.index
    ]
 
    df_valido = trabajo.loc[~rechazada].copy()
    df_valido['adeuda_correlativas'] = df_valido['adeuda_correlativas'].astype(bool)
    return df_valido, df_rechazados


def transformar_y_resumir(df_valido, reglas=None):

    reglas = reglas if reglas is not None else ReglasAcademicas()
    _exigir_columnas(
        df_valido,
        ['legajo', 'carrera', *COLUMNAS_NOTAS, 'asistencia_pct', 'adeuda_correlativas'],
    )
    df = df_valido.reset_index(drop=True).copy()
 
    try:
        notas = df[COLUMNAS_NOTAS].astype(float)
        df['asistencia_pct'] = df['asistencia_pct'].astype(float)
    except (ValueError, TypeError) as error:
        raise ErrorDatos(
            'transformar_y_resumir espera notas y asistencia numéricas; '
            f'ejecutá validar_y_limpiar_actas antes. Detalle: {error}'
        ) from error
    df[COLUMNAS_NOTAS] = notas
    df['adeuda_correlativas'] = df['adeuda_correlativas'].astype(bool)
 
    df['ausentes_totales'] = notas.isna().sum(axis=1)
    df['promedio_final'] = notas.mean(axis=1).round(2)
    df['condicion_academica'] = [
        reglas.condicion(promedio, asistencia, int(ausentes), adeuda)
        for promedio, asistencia, ausentes, adeuda in zip(
            df['promedio_final'],
            df['asistencia_pct'],
            df['ausentes_totales'],
            df['adeuda_correlativas'],
        )
    ]
 
    elegible = pd.Series(
        [
            reglas.elegible_beca(promedio, asistencia, condicion)
            for promedio, asistencia, condicion in zip(
                df['promedio_final'], df['asistencia_pct'], df['condicion_academica']
            )
        ],
        index=df.index,
        dtype=bool,
    )
    df['ranking_carrera'] = pd.Series(pd.NA, index=df.index, dtype='Int64')
    candidatos = df[elegible].sort_values(
        ['carrera', 'promedio_final', 'asistencia_pct', 'legajo'],
        ascending=[True, False, False, True],
    )
    if not candidatos.empty:
        df.loc[candidatos.index, 'ranking_carrera'] = (
            candidatos.groupby('carrera').cumcount() + 1
        )
    df['beca_merito'] = [
        reglas.beca(None if pd.isna(puesto) else int(puesto))
        for puesto in df['ranking_carrera']
    ]
    return df




def verificar_resultado(df_final, reglas=None):

    reglas = reglas if reglas is not None else ReglasAcademicas()
    problemas = []
 
    promedios = df_final['promedio_final'].dropna()
    if not promedios.between(reglas.nota_min, reglas.nota_max).all():
        problemas.append('hay promedios fuera de la escala de notas')
    if not df_final['condicion_academica'].isin(CONDICIONES).all():
        problemas.append('hay condiciones académicas desconocidas')
    if not df_final['beca_merito'].isin(BECAS).all():
        problemas.append('hay tipos de beca desconocidos')
    if df_final['legajo'].duplicated().any():
        problemas.append('hay legajos repetidos en el resultado')
 
    completas = df_final[df_final['beca_merito'] == 'Beca Completa']
    if (completas.groupby('carrera').size() > 1).any():
        problemas.append('hay más de una Beca Completa en una misma carrera')
    becados = df_final['beca_merito'] != 'Sin Beca'
    if (df_final.loc[becados, 'condicion_academica'] != 'Promocionado').any():
        problemas.append('hay becados que no están Promocionados')
 
    if problemas:
        raise ErrorResultado(
            'El resultado no supera las verificaciones: ' + '; '.join(problemas) + '.'
        )
 
 
def resumir_resultados(df_final):

    columnas = ['carrera', 'alumnos', 'promedio_medio', *CONDICIONES, *BECAS]
    if df_final.empty:
        return pd.DataFrame(columns=columnas)
    base = df_final.groupby('carrera').agg(
        alumnos=('legajo', 'count'), promedio_medio=('promedio_final', 'mean')
    )
    base['promedio_medio'] = base['promedio_medio'].round(2)
    condiciones = pd.crosstab(
        df_final['carrera'], df_final['condicion_academica']
    ).reindex(columns=CONDICIONES, fill_value=0)
    becas = pd.crosstab(df_final['carrera'], df_final['beca_merito']).reindex(
        columns=BECAS, fill_value=0
    )
    return base.join(condiciones).join(becas).reset_index()[columnas]
 
 
def exportar_csv(df, ruta, columnas=None):

    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tabla = df if columnas is None else df[columnas]
    tabla.to_csv(ruta, index=False, encoding='utf-8')
    return ruta