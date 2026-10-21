import sys
from pathlib import Path

from fuentes import FuenteCSV, FuenteJSON
from pipeline import validar_y_limpiar_actas, transformar_y_resumir

def ejecutar_pipeline():

    raiz = Path()
    ruta_datos = raiz / 'data' / 'actas_universitarias_completo.csv'
    ruta_salida = raiz / 'outputs' / 'reporte_condicion_alumnos.csv'
    ruta_rechazos = raiz / 'outputs' / 'registros_rechazados_actas.csv'

    print("--- INICIANDO PROCESADOR DE ACTAS ACADÉMICAS ---")

    fuente = FuenteCSV(ruta_datos)
    try:
        df_actas = fuente.cargar() 
    except FileNotFoundError as e:
        print(f"\n ERROR CRÍTICO {e}")
        print("Asegúrate de ejecutar el script desde la raíz del proyecto.")
        sys.exit(1)
    
    print("\nAplicando validaciones RegEx y comprobaciones lógicas...")
    df_valido, df_rechazados = validar_y_limpiar_actas(df_actas)
    print(f"Validación: {len(df_valido)} actas válidas | {len(df_rechazados)} rechazadas.")

    print("Normalizando notas y calculando condición académica...")
    df_final = transformar_y_resumir(df_valido)

    if not df_rechazados.empty:
        df_rechazados.to_csv(ruta_rechazos, index=False, encoding='utf-8')
        print(f"Bitácora de auditoría exportada en: {ruta_rechazos}")
    
    columnas_reporte = ['legajo', 'nombre_estudiante', 'carrera', 'promedio_final', 'condicion_academica', 'beca_merito']
    df_final[columnas_reporte].to_csv(ruta_salida, index=False, encoding='utf-8')
    print(f"Reporte final exportado en: {ruta_salida}")

    print("\n--- PIPELINE FINALIZADO CON ÉXITO ---")


if __name__ == "__main__":
    Path('outputs').mkdir(parents=True, exist_ok=True)
    ejecutar_pipeline()