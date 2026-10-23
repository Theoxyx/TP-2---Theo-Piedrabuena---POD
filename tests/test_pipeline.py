import unittest
import pandas as pd
import numpy as np
from src.pipeline import legajo_valido, normalizar_nota, validar_y_limpiar_actas, transformar_y_resumir

class TestPipelineAcademico(unittest.TestCase):

    def test_legajo_valido_casos_normales_y_limites(self):

        self.assertTrue(legajo_valido('10001-1'))
        self.assertFalse(legajo_valido('00000-9'))
        self.assertFalse(legajo_valido('100A1-1'))
        self.assertFalse(legajo_valido(None))

    def test_normalizar_nota_escalas_mixtas(self):

        self.assertEqual(normalizar_nota('8.5'), 8.5)
        self.assertEqual(normalizar_nota('A'), 10.0)
        self.assertEqual(normalizar_nota('85/100'), 8.5)
        self.assertTrue(np.isnan(normalizar_nota('Ausente')))

    def test_auditoria_y_rechazos(self):

        datos_prueba = pd.DataFrame({
            'legajo': ['12345-1', '00000-1', '54321-2'],
            'asistencia_pct': [80, 90, 150] 
        })
        
        df_valido, df_rechazos = validar_y_limpiar_actas(datos_prueba)
        
        self.assertEqual(len(df_valido), 1)
        self.assertEqual(len(df_rechazos), 2)
        # El legajo 12345-1 debe ser el único que sobrevivió
        self.assertEqual(df_valido.iloc[0]['legajo'], '12345-1')

    def test_resultado_conocido(self):

        datos_prueba = pd.DataFrame({
            'legajo': ['11111-1', '22222-2'],
            'nombre_estudiante': ['Estudiante A', 'Estudiante B'],
            'carrera': ['Data', 'Data'],
            'nota_matematica': [10, 8],
            'nota_programacion': [10, 8],
            'nota_estadistica': [10, 8],
            'nota_bases_datos': [10, 8],
            'nota_fisica': [10, 8],
            'asistencia_pct': [100, 100],
            'adeuda_correlativas': [False, False]
        })
        
        df_resultado = transformar_y_resumir(datos_prueba)
        

        alumno_a = df_resultado[df_resultado['legajo'] == '11111-1'].iloc[0]
        self.assertEqual(alumno_a['promedio_final'], 10.0)
        self.assertEqual(alumno_a['condicion_academica'], 'Promocionado')
        self.assertEqual(alumno_a['beca_merito'], 'Beca Completa')

        alumno_b = df_resultado[df_resultado['legajo'] == '22222-2'].iloc[0]
        self.assertEqual(alumno_b['promedio_final'], 8.0)
        self.assertEqual(alumno_b['condicion_academica'], 'Promocionado') 
        self.assertEqual(alumno_b['beca_merito'], 'Sin Beca')

    def test_no_modificar_original(self):

        datos_prueba = pd.DataFrame({
            'legajo': ['12345-1'],
            'carrera': ['Sistemas'],
            'nota_matematica': ['A'],
            'nota_programacion': [8],
            'nota_estadistica': [8],
            'nota_bases_datos': [8],
            'nota_fisica': [8],
            'asistencia_pct': [100],
            'adeuda_correlativas': [False]
        })
        
        datos_copia = datos_prueba.copy(deep=True)
        _ = transformar_y_resumir(datos_prueba)
        

        pd.testing.assert_frame_equal(datos_prueba, datos_copia)

    def test_tabla_vacia(self):

            df_vacio = pd.DataFrame(columns=[
                'legajo', 'carrera', 'nota_matematica', 'nota_programacion', 
                'nota_estadistica', 'nota_bases_datos', 'nota_fisica', 'asistencia_pct',
                'adeuda_correlativas'
            ])
            
            try:
                df_resultado = transformar_y_resumir(df_vacio)
                self.assertTrue(df_resultado.empty)
            except Exception as e:
                self.fail(f"El procesamiento de una tabla vacía falló con el error: {e}")

if __name__ == '__main__':
    unittest.main()