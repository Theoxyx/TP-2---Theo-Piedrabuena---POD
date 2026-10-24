import math
from dataclasses import dataclass

CONDICIONES = ('Promocionado', 'Retenido', 'Regular', 'Libre', 'Abandono')
BECAS = ('Beca Completa', 'Beca Parcial', 'Sin Beca')


@dataclass(frozen=True)
class ReglasAcademicas:

    nota_min: float = 0.0
    nota_max: float = 10.0
    asistencia_min: float = 0.0
    asistencia_max: float = 100.0

    ausentes_abandono: int = 3
    asistencia_abandono: float = 40.0

    promedio_promocion: float = 8.0
    asistencia_promocion: float = 70.0
    ausentes_max_promocion: int = 0

    promedio_regular: float = 4.0
    asistencia_regular: float = 60.0

    promedio_beca: float = 9.0
    asistencia_beca: float = 80.0

    def __post_init__(self):
        if self.nota_min >= self.nota_max:
            raise ValueError('nota_min debe ser menor que nota_max.')
        if self.asistencia_min >= self.asistencia_max:
            raise ValueError('asistencia_min debe ser menor que asistencia_max.')
        if self.ausentes_abandono < 1:
            raise ValueError('ausentes_abandono debe ser al menos 1.')
        if self.promedio_regular > self.promedio_promocion:
            raise ValueError('promedio_regular no puede superar a promedio_promocion.')
        if self.asistencia_regular > self.asistencia_promocion:
            raise ValueError('asistencia_regular no puede superar a asistencia_promocion.')



    def nota_en_rango(self, nota):
        return self.nota_min <= nota <= self.nota_max

    def asistencia_en_rango(self, asistencia):
        return self.asistencia_min <= asistencia <= self.asistencia_max


    def condicion(self, promedio, asistencia, ausentes, adeuda_correlativas):
        if ausentes >= self.ausentes_abandono and asistencia < self.asistencia_abandono:
            return 'Abandono'
        if promedio is None or math.isnan(promedio):
            return 'Libre'
        if (promedio >= self.promedio_promocion
                and asistencia >= self.asistencia_promocion
                and ausentes <= self.ausentes_max_promocion):
            return 'Retenido' if adeuda_correlativas else 'Promocionado'
        if promedio >= self.promedio_regular and asistencia >= self.asistencia_regular:
            return 'Regular'
        return 'Libre'

    def elegible_beca(self, promedio, asistencia, condicion):
        return bool(
            condicion == 'Promocionado'
            and promedio > self.promedio_beca
            and asistencia >= self.asistencia_beca
        )

    @staticmethod
    def beca(ranking):
        if ranking is None:
            return 'Sin Beca'
        return 'Beca Completa' if ranking == 1 else 'Beca Parcial'