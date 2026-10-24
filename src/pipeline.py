import re
import math
import numbers
import pandas as pd
import numpy as np
from pathlib import Path

from src.dominio import BECAS, CONDICIONES, ReglasAcademicas
from src.fuentes import ErrorDatos

COLUMNAS_NOTAS = ['nota_matematica', 'nota_programacion', 'nota_estadistica', 'nota_bases_datos', 'nota_fisica']
COLUMNAS_REQUERIDAS = ['legajo', 'nombre_estudiante', 'carrera', *COLUMNAS_NOTAS, 'asistencia_pct', 'adeuda_correlativas']

PATRON_LEGAJO = re.compile(r'[0-9]{5}-[0-9]{1}')
ESCALA_LETRAS = {'A': 10.0, 'B+': 9.0, 'B': 8.0, 'C': 6.0, 'D': 4.0}
PATRON_PORCENTAJE = re.compile(r'(\d+(?:\.\d+)?)/100')

class ErrorResultado(RuntimeError): pass


def legajo_valido(v):
    return isinstance(v, str) and bool(PATRON_LEGAJO.fullmatch(v)) and int(v[:5]) != 0

def normalizar_nota(v):
    if pd.isna(v) or str(v).strip().upper() in {'', 'AUSENTE'}: return np.nan
    if isinstance(v, (bool, np.bool_)): raise ValueError(f'booleano no válido: {v!r}')
    
    txt = str(v).strip().upper().replace(',', '.')
    if txt in ESCALA_LETRAS: return ESCALA_LETRAS[txt]
    
    pct = PATRON_PORCENTAJE.fullmatch(txt)
    if pct: return float(pct.group(1)) / 10.0
    
    try:
        num = float(txt)
        if math.isfinite(num): return num
    except ValueError: pass
    raise ValueError(f'formato no reconocido: {v!r}')

def normalizar_booleano(v):
    if isinstance(v, (bool, np.bool_)) or v in (0, 1): return bool(v)
    if isinstance(v, str) and v.strip().lower() in ('true', 'false'): return v.strip().lower() == 'true'
    return None


def validar_y_limpiar_actas(df, reglas=None):
    reglas = reglas or ReglasAcademicas()
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes: raise ErrorDatos(f"Faltan columnas: {', '.join(faltantes)}")

    trabajo = df.reset_index(drop=True).copy()
    errores = pd.Series("", index=trabajo.index)

    legajo_val = trabajo['legajo'].apply(legajo_valido)
    repetido = trabajo['legajo'].duplicated(keep='first') & legajo_val
    asistencia = pd.to_numeric(trabajo['asistencia_pct'], errors='coerce')
    asistencia_val = asistencia.between(reglas.asistencia_min, reglas.asistencia_max)
    adeuda = trabajo['adeuda_correlativas'].apply(normalizar_booleano)

    for col in COLUMNAS_NOTAS:
        def procesar_nota(val):
            try:
                nota = normalizar_nota(val)
                if pd.notna(nota) and not reglas.nota_en_rango(nota):
                    return nota, f"{col}: fuera de rango; "
                return nota, ""
            except ValueError as e:
                return np.nan, f"{col}: {e}; "
        
        resultados = trabajo[col].apply(procesar_nota)
        trabajo[col] = resultados.apply(lambda x: x[0])
        errores += resultados.apply(lambda x: x[1])

    errores += np.where(~legajo_val, "Legajo inválido; ", "")
    errores += np.where(repetido, "Legajo duplicado; ", "")
    errores += np.where(asistencia.isna() | ~asistencia_val, f"Asistencia fuera de rango; ", "")
    errores += np.where(adeuda.isna(), "Correlativas inválidas; ", "")

    rechazadas = errores != ""
    df_rechazados = df.loc[rechazadas].copy()
    df_rechazados.insert(0, 'fila_origen', df_rechazados.index + 1)
    df_rechazados['motivo_rechazo'] = errores[rechazadas].str.strip("; ")

    df_valido = trabajo.loc[~rechazadas].copy()
    df_valido['asistencia_pct'] = asistencia[~rechazadas]
    df_valido['adeuda_correlativas'] = adeuda[~rechazadas].astype(bool)

    return df_valido, df_rechazados


def transformar_y_resumir(df_valido, reglas=None):
    reglas = reglas or ReglasAcademicas()
    df = df_valido.copy()
    notas = df[COLUMNAS_NOTAS].astype(float)

    df = df.assign(
        ausentes_totales=notas.isna().sum(axis=1),
        promedio_final=notas.mean(axis=1).round(2)
    )

    df['condicion_academica'] = df.apply(
        lambda x: reglas.condicion(x.promedio_final, x.asistencia_pct, x.ausentes_totales, x.adeuda_correlativas), axis=1
    )

    elegible = df.apply(lambda x: reglas.elegible_beca(x.promedio_final, x.asistencia_pct, x.condicion_academica), axis=1)
    df['ranking_carrera'] = pd.NA
    
    candidatos = df[elegible].sort_values(['carrera', 'promedio_final', 'asistencia_pct', 'legajo'], 
                                          ascending=[True, False, False, True])
    if not candidatos.empty:
        df.loc[candidatos.index, 'ranking_carrera'] = candidatos.groupby('carrera').cumcount() + 1

    df['beca_merito'] = df['ranking_carrera'].apply(lambda p: reglas.beca(None if pd.isna(p) else int(p)))
    
    return df


def verificar_resultado(df_final, reglas=None):
    reglas = reglas or ReglasAcademicas()
    prob = []
    
    if not df_final['promedio_final'].dropna().between(reglas.nota_min, reglas.nota_max).all(): prob.append('promedios fuera de escala')
    if not df_final['condicion_academica'].isin(CONDICIONES).all(): prob.append('condiciones desconocidas')
    if not df_final['beca_merito'].isin(BECAS).all(): prob.append('becas desconocidas')
    if df_final['legajo'].duplicated().any(): prob.append('legajos repetidos')
    if (df_final[df_final['beca_merito'] == 'Beca Completa'].groupby('carrera').size() > 1).any(): prob.append('más de una Beca Completa por carrera')
    if (df_final.loc[df_final['beca_merito'] != 'Sin Beca', 'condicion_academica'] != 'Promocionado').any(): prob.append('becados no Promocionados')
    
    if prob: raise ErrorResultado('Fallo: ' + '; '.join(prob))


def resumir_resultados(df_final):
    columnas = ['carrera', 'alumnos', 'promedio_medio', *CONDICIONES, *BECAS]
    if df_final.empty: return pd.DataFrame(columns=columnas)
    
    base = df_final.groupby('carrera').agg(alumnos=('legajo', 'count'), promedio_medio=('promedio_final', 'mean')).round(2)
    return base.join(pd.crosstab(df_final['carrera'], df_final['condicion_academica']).reindex(columns=CONDICIONES, fill_value=0)) \
               .join(pd.crosstab(df_final['carrera'], df_final['beca_merito']).reindex(columns=BECAS, fill_value=0)) \
               .reset_index()[columnas]


def exportar_csv(df, ruta, columnas=None):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    (df[columnas] if columnas else df).to_csv(ruta, index=False, encoding='utf-8')
    return ruta