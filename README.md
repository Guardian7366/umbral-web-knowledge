# Umbral Web

Prototipo académico de gestión del conocimiento para una empresa ficticia de software especializada en diseño web. Busca recuperar referencias, métodos creativos y aprendizajes que ayuden al equipo a salir de soluciones repetidas.

## Contenido actual

- `docs/Umbral Web empresa y guia.docx`: descripción de la empresa y pasos para subir el proyecto a GitHub.
- `datos/documentos/`: nueve textos internos ficticios en UTF-8.
- `datos/catalogo.json`: ruta, título, categoría y uso sugerido de cada texto. Las rutas parten de la carpeta principal del proyecto.

La empresa, los proyectos y las observaciones de los documentos son ficticios. Los textos tienen formato de documentación interna y se prepararon como material de prueba.

## Categorías

- `referencias_diseno`: ideas y criterios para orientar una propuesta visual.
- `metodos_creativos`: procedimientos para generar, probar o revisar conceptos.
- `aprendizajes_proyectos`: antecedentes y conclusiones de trabajos anteriores.

| Código | Documento | Categoría |
| --- | --- | --- |
| UW01 | Jerarquía visual para páginas con mucho contenido | referencias_diseno |
| UW02 | Movimiento y respuesta visual en una interfaz | referencias_diseno |
| UW03 | Composición modular para una identidad flexible | referencias_diseno |
| UW04 | Sesión breve de generación de ideas | metodos_creativos |
| UW05 | Prueba corta de una propuesta visual | metodos_creativos |
| UW06 | Revisión de conceptos antes de elegir una dirección | metodos_creativos |
| UW07 | Cierre del proyecto de catálogo de cursos Aula Clara | aprendizajes_proyectos |
| UW08 | Cierre del proyecto de portafolio Estudio Norte | aprendizajes_proyectos |
| UW09 | Cierre del proyecto de menú digital Mesa Abierta | aprendizajes_proyectos |

## Uso por el equipo

Los integrantes 3 y 4 deben leer los archivos `.txt`; el catálogo contiene las etiquetas para entrenar y comprobar la clasificación. No se debe incluir la categoría ni el campo `uso_sugerido` como parte del texto que se clasifica.

Para la clasificación se sugieren seis documentos de entrenamiento (dos por categoría) y tres de prueba (uno por categoría), identificados en el catálogo. Ajusten TF-IDF y entrenen el modelo solo con los de entrenamiento; después clasifiquen los de prueba. En la búsqueda pueden consultar los nueve textos.

Consultas iniciales sugeridas:
- ¿Cómo organizar una sesión para generar ideas de diseño?
- ¿Qué debemos revisar para que las animaciones no dificulten la navegación?

Son consultas para ejecutar, no resultados ya obtenidos. La colección permite una demostración inicial; su tamaño no permite concluir que el clasificador funcionará igual con documentos nuevos de cualquier tipo.

## Aportaciones pendientes

- Integrante 2: mapa del ciclo del conocimiento y ontología o grafo conceptual, dentro de `docs/`.
- Integrantes 3 y 4: código de clasificación y búsqueda, dentro de `src/`, con dependencias y pasos de ejecución.
- Integrante 5: evidencias dentro de `evidencias/` e informe final en PDF dentro de `docs/`.
- Integrante 1: reunir los archivos finales y comprobar el acceso al repositorio.

El código y las evidencias de ejecución se incorporarán con las aportaciones del equipo. Las carpetas `src/` y `evidencias/` se crearán cuando tengan contenido. No cambien los nombres o categorías sin avisar a quienes programan.

Ayuda oficial: [crear un repositorio](https://docs.github.com/es/repositories/creating-and-managing-repositories/quickstart-for-repositories) y [cargar archivos](https://docs.github.com/es/repositories/working-with-files/managing-files/adding-a-file-to-a-repository).
