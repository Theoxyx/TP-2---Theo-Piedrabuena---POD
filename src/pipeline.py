import re
import pandas as pd
import numpy as np

PATRON_LEGAJO = re.compile(r'[0-9]{5}-[0-9]{1}')

def legajo_valido(valor):
    if not isinstance(valor, str) or PATRON_LEGAJO.fullmatch(valor) is None:
        return False
    try:
        base = int(valor.split('-')[0])
        if base == 0:
            return False
    except ValueError:
        return False
    return True


def normalizar_nota(valor):
    if pd.isna(valor) or valor is None:
        return np.nan
        
    if isinstance(valor, (int, float)):
        return float(valor)
        
    valor_str = str(valor).strip().upper()
    
    escala_letras = {
        'A': 10.0,
        'B+': 9.0,
        'B': 8.0,
        'C': 6.0,
        'D': 4.0
    }
    if valor_str in escala_letras:
        return escala_letras[valor_str]
        
    if '/100' in valor_str:
        try:
            num = float(valor_str.split('/')[0])
            return num / 10.0
        except ValueError:
            return np.nan
            
    try:
        return float(valor_str)
    except ValueError:
        return np.nan
    
    
def validar_y_limpiar_actas(df: pd.DataFrame):

    mascara_legajo = df['legajo'].apply(legajo_valido)

    mascara_asistencia = pd.to_numeric(df['asistencia_pct'], errors='coerce').between(0, 100)

    filtro_rechazos = ~(mascara_legajo & mascara_asistencia)
    df_rechazados = df[filtro_rechazos].copy()
    
    df_rechazados['motivo_rechazo'] = np.select(
        [~mascara_legajo[filtro_rechazos], ~mascara_asistencia[filtro_rechazos]],
        ['Legajo malformado o inválido', 'Asistencia fuera de rango'],
        default='Múltiples errores'
    )

    df_valido = df[mascara_legajo & mascara_asistencia].copy()
    
    return df_valido, df_rechazados


 
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