import unittest
import pandas as pd
import numpy as np
from src.pipeline import (
    legajo_valido, 
    normalizar_nota, 
    validar_y_limpiar_actas, 
    transformar_y_resumir,
    ErrorDatos
)

class TestPipelineAcademico(unittest.TestCase):

    def setUp(self):
        self.columnas = [
            'legajo', 'nombre_estudiante', 'carrera', 
            'nota_matematica', 'nota_programacion', 'nota_estadistica', 
            'nota_bases_datos', 'nota_fisica', 'asistencia_pct', 'adeuda_correlativas'
        ]
        
    def test_legajo_valido_casos_normales_y_limites(self):
        """Verifica que la función acepte legajos correctos y rechace los corruptos."""
        self.assertTrue(legajo_valido('10001-1'))
        self.assertFalse(legajo_valido('00000-9'))
        self.assertFalse(legajo_valido('100A1-1'))
        self.assertFalse(legajo_valido(None))

    def test_normalizar_nota_escalas_mixtas(self):
        """Verifica la correcta conversión de números, letras y fracciones a float."""
        self.assertEqual(normalizar_nota('8.5'), 8.5)
        self.assertEqual(normalizar_nota('A'), 10.0)
        self.assertEqual(normalizar_nota('85/100'), 8.5)
        self.assertTrue(np.isnan(normalizar_nota('Ausente')))

    def test_auditoria_y_rechazos(self):
        """Prueba que el filtro vectorizado detecte errores y genere la bitácora."""
        datos = [
            ['12345-1', 'Juan', 'Data', 8, 8, 8, 8, 8, 80, False], 
            ['00000-1', 'Ana', 'Data', 8, 8, 8, 8, 8, 80, False],   
            ['54321-2', 'Luis', 'Data', 8, 8, 8, 8, 8, 150, False]  
        ]
        datos_prueba = pd.DataFrame(datos, columns=self.columnas)
        
        df_valido, df_rechazos = validar_y_limpiar_actas(datos_prueba)
        
        self.assertEqual(len(df_valido), 1)
        self.assertEqual(len(df_rechazos), 2)
        self.assertEqual(df_valido.iloc[0]['legajo'], '12345-1')
        self.assertTrue('motivo_rechazo' in df_rechazos.columns)

    def test_resultado_conocido(self):
        """Verifica el cálculo de promedio, y la asignación exacta de becas según el ranking."""
        datos = [
            ['11111-1', 'Estudiante A', 'Data', 10, 10, 10, 10, 10, 100, False],   
            ['22222-2', 'Estudiante B', 'Data', 9.5, 9.5, 9.5, 9.5, 9.5, 100, False] 
        ]
        datos_prueba = pd.DataFrame(datos, columns=self.columnas)
        
        df_valido, _ = validar_y_limpiar_actas(datos_prueba)
        df_resultado = transformar_y_resumir(df_valido)
        
        alumno_a = df_resultado[df_resultado['legajo'] == '11111-1'].iloc[0]
        self.assertEqual(alumno_a['promedio_final'], 10.0)
        self.assertEqual(alumno_a['beca_merito'], 'Beca Completa') 

        alumno_b = df_resultado[df_resultado['legajo'] == '22222-2'].iloc[0]
        self.assertEqual(alumno_b['promedio_final'], 9.5)
        self.assertEqual(alumno_b['beca_merito'], 'Beca Parcial') 

    def test_no_modificar_original(self):
        """Asegura que el pipeline respete la inmutabilidad funcional (Programación Orientada a Datos)."""
        datos = [['12345-1', 'Juan', 'Data', 'A', 8, 8, 8, 8, 100, False]]
        datos_prueba = pd.DataFrame(datos, columns=self.columnas)
        
        datos_copia = datos_prueba.copy(deep=True)
        df_valido, _ = validar_y_limpiar_actas(datos_prueba)
        _ = transformar_y_resumir(df_valido)
        
        pd.testing.assert_frame_equal(datos_prueba, datos_copia)

    def test_tabla_vacia(self):
        """Verifica que las transformaciones de Pandas no colapsen si la tabla carece de filas."""
        df_vacio = pd.DataFrame(columns=self.columnas)
        
        try:
            df_valido, _ = validar_y_limpiar_actas(df_vacio)
            df_resultado = transformar_y_resumir(df_valido)
            self.assertTrue(df_resultado.empty)
        except Exception as e:
            self.fail(f"El procesamiento de una tabla vacía falló con el error: {e}")

    def test_esquema_incompleto(self):
        """Evalúa que el pipeline de seguridad rechace tablas a las que les falten columnas requeridas."""
        df_incompleto = pd.DataFrame({'legajo': ['12345-1']}) 
        
        with self.assertRaises(ErrorDatos):
            validar_y_limpiar_actas(df_incompleto)

if __name__ == '__main__':
    unittest.main()