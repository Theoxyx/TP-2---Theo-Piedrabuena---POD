import unittest
import numpy as np
from src.pipeline import legajo_valido, normalizar_nota

class TestPipelineAcademico(unittest.TestCase):

    def test_legajo_valido_casos_normales_y_limites(self):

        self.assertTrue(legajo_valido('10001-1'))
        self.assertTrue(legajo_valido('99999-9'))
        
        self.assertFalse(legajo_valido('00000-9')) 
        self.assertFalse(legajo_valido('100A1-1')) 
        self.assertFalse(legajo_valido('10001'))   
        self.assertFalse(legajo_valido(None))    

    def test_normalizar_nota_escalas_mixtas(self):
        
        self.assertEqual(normalizar_nota('8.5'), 8.5)
        self.assertEqual(normalizar_nota(7), 7.0)
        
        self.assertEqual(normalizar_nota('A'), 10.0)
        self.assertEqual(normalizar_nota('C'), 6.0)
        
        self.assertEqual(normalizar_nota('85/100'), 8.5)
        
        self.assertTrue(np.isnan(normalizar_nota('Ausente')))
        self.assertTrue(np.isnan(normalizar_nota('texto_cualquiera')))
        self.assertTrue(np.isnan(normalizar_nota(None)))

if __name__ == '__main__':
    unittest.main()