import math
import unittest

from src.dominio import ReglasAcademicas


class TestCondicion(unittest.TestCase):

    def setUp(self):
        self.reglas = ReglasAcademicas()

    def test_cada_condicion_en_un_caso_normal(self):
        casos = [
            ((9.0, 95, 0, False), 'Promocionado'),
            ((9.0, 95, 0, True), 'Retenido'),
            ((6.0, 80, 0, False), 'Regular'),
            ((3.0, 80, 0, False), 'Libre'),
            ((5.0, 20, 3, False), 'Abandono'),
        ]
        for argumentos, esperado in casos:
            with self.subTest(argumentos=argumentos):
                self.assertEqual(self.reglas.condicion(*argumentos), esperado)

    def test_limites_de_promocion(self):
        self.assertEqual(self.reglas.condicion(8.0, 70, 0, False), 'Promocionado')
        self.assertEqual(self.reglas.condicion(7.99, 70, 0, False), 'Regular')
        self.assertEqual(self.reglas.condicion(8.0, 69.9, 0, False), 'Regular')

    def test_limites_de_regularidad(self):
        self.assertEqual(self.reglas.condicion(4.0, 60, 0, False), 'Regular')
        self.assertEqual(self.reglas.condicion(3.99, 60, 0, False), 'Libre')
        self.assertEqual(self.reglas.condicion(4.0, 59.9, 0, False), 'Libre')

    def test_limites_de_abandono(self):

        self.assertEqual(self.reglas.condicion(5.0, 39.9, 3, False), 'Abandono')
        self.assertNotEqual(self.reglas.condicion(5.0, 40, 3, False), 'Abandono')
        self.assertNotEqual(self.reglas.condicion(5.0, 20, 2, False), 'Abandono')

    def test_una_nota_ausente_impide_promocionar(self):
        self.assertEqual(self.reglas.condicion(9.5, 100, 1, False), 'Regular')

    def test_sin_notas_es_libre_o_abandono(self):
        self.assertEqual(self.reglas.condicion(math.nan, 90, 5, False), 'Libre')
        self.assertEqual(self.reglas.condicion(None, 90, 5, False), 'Libre')
        self.assertEqual(self.reglas.condicion(math.nan, 10, 5, False), 'Abandono')

    def test_correlativas_no_afectan_a_quien_no_promociona(self):
        self.assertEqual(self.reglas.condicion(6.0, 80, 0, True), 'Regular')


class TestBeca(unittest.TestCase):

    def setUp(self):
        self.reglas = ReglasAcademicas()

    def test_elegible_en_casos_normales_y_limites(self):
        self.assertTrue(self.reglas.elegible_beca(9.01, 80, 'Promocionado'))
        # El promedio debe ser ESTRICTAMENTE mayor a 9.0
        self.assertFalse(self.reglas.elegible_beca(9.0, 100, 'Promocionado'))
        self.assertFalse(self.reglas.elegible_beca(9.5, 79.9, 'Promocionado'))

    def test_solo_los_promocionados_son_elegibles(self):
        for condicion in ('Retenido', 'Regular', 'Libre', 'Abandono'):
            with self.subTest(condicion=condicion):
                self.assertFalse(self.reglas.elegible_beca(9.8, 100, condicion))

    def test_tipo_de_beca_segun_puesto(self):
        self.assertEqual(self.reglas.beca(1), 'Beca Completa')
        self.assertEqual(self.reglas.beca(2), 'Beca Parcial')
        self.assertEqual(self.reglas.beca(7), 'Beca Parcial')
        self.assertEqual(self.reglas.beca(None), 'Sin Beca')


class TestConfiguracion(unittest.TestCase):

    def test_umbrales_incoherentes_se_rechazan(self):
        with self.assertRaises(ValueError):
            ReglasAcademicas(nota_min=10, nota_max=0)
        with self.assertRaises(ValueError):
            ReglasAcademicas(promedio_regular=9, promedio_promocion=8)
        with self.assertRaises(ValueError):
            ReglasAcademicas(ausentes_abandono=0)

    def test_se_pueden_cambiar_los_umbrales(self):
        reglas = ReglasAcademicas(promedio_promocion=7.0)
        self.assertEqual(reglas.condicion(7.0, 80, 0, False), 'Promocionado')

    def test_las_reglas_son_inmutables(self):
        with self.assertRaises(Exception):
            ReglasAcademicas().promedio_beca = 5.0


if __name__ == '__main__':
    unittest.main()