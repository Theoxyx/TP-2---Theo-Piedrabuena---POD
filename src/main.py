import sys
from pathlib import Path
import argparse
import pandas as pd

from src.fuentes import FuenteCSV, FuenteJSON, ErrorDatos
from src.pipeline import validar_y_limpiar_actas, transformar_y_resumir, ErrorResultado
from src.dominio import ReglasAcademicas

raiz = Path(__file__).resolve().parent.parent
ruta_entrada = raiz / 'data' / 'actas_universitarias_completo.csv'
ruta_salida = raiz / 'outputs'

NOMBRE_REPORTE = 'reporte_condicion_alumnos.csv'
NOMBRE_RECHAZOS = 'registros_rechazados_actas.csv'
NOMBRE_RESUMEN = 'resumen_por_carrera.csv'

COLUMNAS_REPORTE = [
    'legajo',
    'nombre_estudiante',
    'carrera',
    'promedio_final',
    'condicion_academica',
    'beca_merito',
]


def exportar_csv(df, ruta, columnas=None):
    """Función de efecto secundario para guardar archivos en disco."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tabla = df if columnas is None else df[columnas]
    tabla.to_csv(ruta, index=False, encoding='utf-8')
    return ruta


def fuente_desde_ruta(ruta):
    """Fábrica polimórfica para instanciar la clase de lectura correcta según la extensión."""
    ruta = Path(ruta)
    if ruta.suffix.lower() == '.json':
        return FuenteJSON(ruta)
    elif ruta.suffix.lower() == '.csv':
        return FuenteCSV(ruta)
    else:
        raise ErrorDatos(f"Formato no soportado: {ruta.suffix}. Usa .csv o .json")


def procesar(ruta_archivo, reglas=None):
    reglas = reglas if reglas is not None else ReglasAcademicas()

    fuente = fuente_desde_ruta(ruta_archivo)
    df_actas = fuente.cargar()
    
    df_valido, df_rechazados = validar_y_limpiar_actas(df_actas, reglas)
    
    if len(df_valido) + len(df_rechazados) != len(df_actas):
        raise ErrorResultado(
            'Se perdieron registros en la validación: '
            f'{len(df_actas)} de entrada, {len(df_valido)} válidos y '
            f'{len(df_rechazados)} rechazados.'
        )

    df_final = transformar_y_resumir(df_valido, reglas)
    
    # Creamos un resumen rápido usando Pandas directamente en el main
    resumen = df_final.groupby('carrera').agg(
        alumnos=('legajo', 'count'), 
        promedio_medio=('promedio_final', 'mean')
    ).round(2).reset_index()

    return df_final, df_rechazados, resumen


def ejecutar_pipeline(ruta_entrada_arch, dir_salida):
    print('--- INICIANDO PROCESADOR DE ACTAS ACADÉMICAS ---')
    print(f'Entrada: {ruta_entrada_arch}')

    df_final, df_rechazados, resumen = procesar(ruta_entrada_arch)
    total = len(df_final) + len(df_rechazados)
    
    print(f'Validación: {len(df_final)} actas válidas | '
          f'{len(df_rechazados)} rechazadas (de {total}).')
    
    if total == 0:
        print('Aviso: el archivo no contiene registros.')

    dir_salida = Path(dir_salida)

    # Exportamos los archivos
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
        print(f'\nERROR CRÍTICO: {error}', file=sys.stderr)
        print('Revisá la ruta indicada en --entrada.', file=sys.stderr)
        return 1
    except (ErrorDatos, ErrorResultado) as error:
        print(f'\nERROR: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())