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
    
    
    
def transformar_y_resumir(df_valido: pd.DataFrame):

    materias = ['nota_matematica', 'nota_programacion', 'nota_estadistica', 'nota_bases_datos', 'nota_fisica']
    
    for m in materias:
        df_valido[m] = df_valido[m].apply(normalizar_nota)

    df_resultado = (
        df_valido
        .assign(
            ausentes_totales=lambda tabla: tabla[materias].isna().sum(axis=1),
            promedio_final=lambda tabla: tabla[materias].mean(axis=1).round(2),
            condicion_academica=lambda tabla: np.select(
                [
                    (tabla['ausentes_totales'] >= 3) & (tabla['asistencia_pct'] < 40),
                    (tabla['promedio_final'] >= 7.0) & (tabla['asistencia_pct'] >= 75) & (tabla['adeuda_correlativas'] == False),
                    (tabla['promedio_final'] >= 4.0) & (tabla['asistencia_pct'] >= 60)
                ],
                ['Abandono', 'Promocionado', 'Regular'],
                default='Libre'
            )
        )
    )

    return df_resultado