# **Procesador de Actas y Regularidades Académicas**


* **Autor:** Theo Piedrabuena  
* **Materia:** Programación Orientada a Datos  

# **Problema**

Al finalizar un cuatrimestre, las secretarías académicas universitarias reciben planillas de calificaciones ("actas") provenientes de diversas cátedras. Estas planillas en crudo suelen presentar múltiples problemas:

   * Inconsistencias de formato y errores de tipeo en los legajos.

   * Escalas de calificación mixtas, producto de alumnos de intercambio o equivalencias (ej. notas numéricas mezcladas con letras como "A", "B" o "C", o porcentajes como "85/100").

   * Campos vacíos o nulos generados por estudiantes que abandonaron la materia a mitad de cursada.

   * Alumnos que alcanzan las notas para promocionar, pero que por errores del sistema figuran inscriptos sin tener aprobadas las materias correlativas previas.

El procesamiento manual o la eliminación silenciosa de estos registros rompe la "trazabilidad" de los datos, impidiendo auditar por qué se modificó o descartó la nota de un estudiante.

# **Objetivo** 

Construir una aplicación en Python para poder realizar las siguientes tareas:

   * Importar las actas desde archivos CSV o JSON.   
   
   * Aplicar expresiones regulares para asegurar que el legajo del alumno cumpla el formato institucional estricto, y separar los registros con calificaciones lógicamente imposibles (ejemplo: notas negativas).   
   
   * Convertir las escalas mixtas (letras o porcentajes) a una escala numérica uniforme, e inferir un "Posibe Abandono" del alumno en base a la inasistencia y la cantidad de parciales ausentes.
   
   * Aplicar reglas de negocio cruzando el promedio final, el porcentaje de asistencia y el estado de sus materias correlativas para determinar la condición académica final.

   * Utilizar el promedio final para designar que alumnos pueden obtener una beca en la universidad. 

   * Este programa podra ser utilizado por personal o secretaría académica, para automatizar la carga de actas, estandarizar las escalas de notas y calcular el estado final de los estudiantes (Promocionado, Regular, Libre, Retenido o Abandono) de forma objetiva, rápida y repetible; o tambien podra ser utilizado por docentes y coordinadores de cátedra, para auditar rápidamente sus propias planillas antes de entregarlas, revisando la bitácora de errores generada por la aplicación para detectar inconsistencias previas a la carga oficial.

# **Alcance**

   * La primera versión utilizará un dataset sintético estático y controlado de 82 observaciones que simula actas con errores intencionales. Se implementará lectura polimórfica (CSV/JSON), validaciones estrictas con RegEx, manejo de valores nulos, y un conjunto de pruebas unitarias para verificar el comportamiento esperado y los casos límite.

# **Datos**

   * La aplicacion no utiliza una base de datos real con información personal, sino datos generados mediante una simulación.

   * El dataset fue construido y tipeado de forma estática y controlada, contando con 82 observaciones. Esto garantiza que cualquier persona que clone el repositorio y ejecute el pipeline obtendrá exactamente los mismos resultados, rechazos y métricas en cada ejecución.

   * **Unidad de análisis:** Cada fila del conjunto de datos representa la situación académica de un estudiante único al finalizar el ciclo lectivo de un cuatrimestre.

   * **Variables principales utilizadas:** 

      * **legajo:** Identificador alfanumérico del estudiante. Sirve para validar el formato institucional mediante expresiones regulares.   
      
      * **asistencia_pct:** Porcentaje de asistencia a las clases.
      
      * **'nota_matematica','nota_programacion','nota_estadistica','nota_bases_datos','nota_fisica':** Calificaciones obtenidas. Contienen tanto valores numéricos, valores nulos (None para ausentes) y escalas mixtas en texto (ej. "A", "B+", "85/100") simulando alumnos de intercambio.

      * **adeuda_correlativas:** Variable booleana (True/False) que indica si el sistema registra que el alumno debe materias previas.


# **Limitaciones:**

* Al tratarse de un dataset sintético estructurado para probar código, las distribuciones de las calificaciones y la tasa de abandono no representan el rendimiento académico real ni el comportamiento estadístico de una población estudiantil.

# **Resultados producidos e interpretación**
El programa no modifica el dataset original, sino que genera dos reportes de salida:
1. `reporte_condicion_alumnos.csv`: Un consolidado con el legajo, carrera, promedio final y la condición/beca final. Permite conocer inmediatamente el estatus de la cursada y los beneficiarios de becas sin cálculos manuales.
2. `registros_rechazados_actas.csv`: Un registro de auditoría con las filas omitidas y el motivo explícito (ej. "Legajo malformado o inválido"). Garantiza la trazabilidad exigida por la materia; no se borra ni se asume ningún dato sin documentar por qué se excluyó del cálculo.


# **Instrucciones de Ejecución**

## Requisitos

Asegúrate de contar con Python 3.9 o superior y las dependencias instaladas:

```bash
pip install pandas numpy
```

## Ejecutar la Aplicación

Para procesar las actas, ejecutar las transformaciones y generar los reportes en la carpeta `outputs/`, ejecuta:

```bash
python -m src.main
```

## Ejecutar las Pruebas Unitarias

Para verificar la pureza y estabilidad de las funciones de validación, ejecuta:

```bash
python -m unittest -v tests/test_pipeline.py
```