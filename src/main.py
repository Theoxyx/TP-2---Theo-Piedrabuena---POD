import sys
from pathlib import Path
import argparse

from src.fuentes import FuenteCSV, FuenteJSON
from src.pipeline import validar_y_limpiar_actas, transformar_y_resumir

from src.dominio import ReglasAcademicas
from src.fuentes import ErrorDatos, fuente_desde_ruta
from src.pipeline import (
    COLUMNAS_REPORTE,
    ErrorResultado,
    exportar_csv,
    resumir_resultados,
    transformar_y_resumir,
    validar_y_limpiar_actas,
    verificar_resultado,
)
 
raiz = Path(__file__).resolve().parent.parent
ruta_entrada = raiz / 'data' / 'actas_universitarias_completo.csv'
ruta_salida = raiz / 'outputs'
 
NOMBRE_REPORTE = 'reporte_condicion_alumnos.csv'
NOMBRE_RECHAZOS = 'registros_rechazados_actas.csv'
NOMBRE_RESUMEN = 'resumen_por_carrera.csv'
 
 
def procesar(ruta_entrada, reglas=None):

    reglas = reglas if reglas is not None else ReglasAcademicas()
 
    df_actas = fuente_desde_ruta(ruta_entrada).cargar()
    df_valido, df_rechazados = validar_y_limpiar_actas(df_actas, reglas)
    if len(df_valido) + len(df_rechazados) != len(df_actas):
        raise ErrorResultado(
            'Se perdieron registros en la validación: '
            f'{len(df_actas)} de entrada, {len(df_valido)} válidos y '
            f'{len(df_rechazados)} rechazados.'
        )
 
    df_final = transformar_y_resumir(df_valido, reglas)
    verificar_resultado(df_final, reglas)
    return df_final, df_rechazados, resumir_resultados(df_final)
 
 
def ejecutar_pipeline(ruta_entrada, dir_salida):

    print('--- INICIANDO PROCESADOR DE ACTAS ACADÉMICAS ---')
    print(f'Entrada: {ruta_entrada}')
 
    df_final, df_rechazados, resumen = procesar(ruta_entrada)
    total = len(df_final) + len(df_rechazados)
    print(f'Validación: {len(df_final)} actas válidas | '
          f'{len(df_rechazados)} rechazadas (de {total}).')
    if total == 0:
        print('Aviso: el archivo no contiene registros.')
 
    dir_salida = Path(dir_salida)

    exportar_csv(df_rechazados, dir_salida / NOMBRE_RECHAZOS)
    exportar_csv(df_final, dir_salida / NOMBRE_REPORTE, COLUMNAS_REPORTE)
    exportar_csv(resumen, dir_salida / NOMBRE_RESUMEN)
 
    if not df_rechazados.empty:
        print('\nMotivos de rechazo:')
        for motivo, cantidad in df_rechazados['motivo_rechazo'].value_counts().items():
            print(f'  {cantidad:>3}  {motivo}')
    if not resumen.empty:
        print('\nResumen por carrera:')
        print(resumen.to_string(index=False))
 
    print(f'\nBitácora de auditoría: {dir_salida / NOMBRE_RECHAZOS}')
    print(f'Reporte final:         {dir_salida / NOMBRE_REPORTE}')
    print(f'Resumen por carrera:   {dir_salida / NOMBRE_RESUMEN}')
    print('\n--- PIPELINE FINALIZADO CON ÉXITO ---')
 
 
def construir_parser():
    parser = argparse.ArgumentParser(
        prog='python -m src.main',
        description='Procesa actas académicas (CSV o JSON) y genera los reportes.',
    )
    parser.add_argument(
        '--entrada', type=Path, default=ruta_entrada,
        help='archivo .csv o .json con las actas (por defecto: %(default)s)',
    )
    parser.add_argument(
        '--salida', type=Path, default=ruta_salida,
        help='carpeta donde se guardan los reportes (por defecto: %(default)s)',
    )
    return parser
 
 
def main(argv=None):

    args = construir_parser().parse_args(argv)
    try:
        ejecutar_pipeline(args.entrada, args.salida)
    except FileNotFoundError as error:
        print(f'\nERROR: {error}', file=sys.stderr)
        print('Revisá la ruta indicada en --entrada.', file=sys.stderr)
        return 1
    except (ErrorDatos, ErrorResultado) as error:
        print(f'\nERROR: {error}', file=sys.stderr)
        return 1
    return 0
 
 
if __name__ == '__main__':
    sys.exit(main())