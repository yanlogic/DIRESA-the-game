# DIRESA: el juego

Juego 2D en pixel art hecho con Python y Pygame para el curso **Ingeniería de Software (CIIN1252P, UPN)**.
Es la presentación del desafío final del curso: el caso **DIRESA La Libertad**, trabajado con el
enfoque **RUP**. Recorres un centro de salud que todavía trabaja con papel y vas viendo, paso a paso,
cómo el equipo identificó a los stakeholders, tomó decisiones con criterios y dejó cada requisito
trazable de principio a fin.

## Cómo ejecutarlo

Necesitas Python 3.10 o superior.

```
python -m pip install pygame-ce
python main.py
```

El juego se abre en una ventana de 1152 x 648. Con **F11** pasa a pantalla completa.
No necesita internet ni archivos de audio: la música y los sonidos se generan con código.

## Cómo se juega

El juego empieza con una pequeña cinemática que muestra los problemas del centro de salud y luego
llegas a la calle, frente al edificio. A la izquierda hay un **buzón**: ahí eliges el capítulo.

1. **Capítulo 1 · El centro de salud de papel.** Entra a cada sala y habla con los 8 stakeholders
   (con E) para conocer su rol, su poder y su interés.
2. **Capítulo 2 · Las decisiones del equipo.** Prioriza 2 de los 5 módulos del sistema y resuelve
   3 conflictos entre stakeholders comparando alternativas con criterios con peso.
3. **Capítulo 3 · Sigue el hilo.** Sigue el requisito RF-001 por 4 puertas: requisito, caso de uso,
   clases y matriz de trazabilidad.

Al cerrar el capítulo 3 y salir del centro de salud, se muestra la cinemática final con la solución
funcionando y la tarjeta de cierre.

## Controles

| Tecla | Qué hace |
|---|---|
| W A S D o flechas | Moverte |
| Shift | Correr |
| E | Hablar, entrar, salir, abrir el buzón, seguir los diálogos |
| TAB | Mostrar u ocultar la tarjeta de misión |
| H | Ver todos los controles (se cierra con cualquier tecla) |
| M | Activar o silenciar el sonido y la música |
| F11 | Pantalla completa |
| Esc | Salir |

## Archivos

```
main.py        el juego completo
assets/        imágenes del hospital y retratos de los personajes
diagramas/     PDFs que se abren desde el juego (casos de uso, clases y BPMN)
```

Las carpetas `assets/` y `diagramas/` deben estar junto a `main.py`.

## Ajustes de sonido (opcional)

Están dentro de `main.py` y se pueden cambiar para la exposición:

- `MUSICA_VOLUMEN`: volumen de la música (calle, inicio, intro y final).
- `AMBIENTE_VOLUMEN`: volumen del sonido ambiente dentro del centro de salud.
- En `class Voces`, la línea `dato = int(v * env * 5200)`: volumen de las voces de los personajes.

## Equipo

Yanela Acori Sanchez, Mónica Candiotti Simeón y Geradth Gaitán Gonzales.
