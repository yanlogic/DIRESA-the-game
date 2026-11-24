import math
import os
import random
import re
import subprocess
import sys

import pygame

# ----------------------------------------------------------------------------
# Configuración general
# ----------------------------------------------------------------------------
W, H = 384, 216          # tamaño interno (pixel art)
SCALE = 3                # ampliación -> ventana de 1152 x 648
SCREEN_W, SCREEN_H = W * SCALE, H * SCALE
GROUND = 188             # fila donde pisan los pies
WORLD_W = 2960           # largo total del recorrido (en píxeles internos)
SPEED = 1.5              # velocidad de caminata
RUN_MULT = 2.2           # multiplicador para correr / caminar rápido
PROX = 70                # distancia para "identificar" a un stakeholder
CONFLICT_PAD = 45
FRAME_TICKS = 8          # cada cuántos fotogramas cambia el cuadro de caminata
CHAR_SCALE = 1.50           # 1 = original, 2 = doble
SPRITE = int(32 * CHAR_SCALE)
FEET = int(30 * CHAR_SCALE)
HOSPITAL_CLOSED = "assets/hospital_cerrado.png"   # tu hospital con la puerta cerrada
HOSPITAL_OPEN = "assets/hospital_abierto.png"     # el mismo hospital con la puerta abierta
HOSPITAL_SCALE = 3      # ampliación del hospital: 1, 2 o 3 (números enteros = píxeles nítidos)
DOOR_X_IMG = 105         # dónde está el centro de la puerta dentro de la imagen (en píxeles de la imagen)


def res(path):
    """Ruta correcta tanto al correr el .py como dentro del .exe (PyInstaller)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, path)


# ----------------------------------------------------------------------------
# DATOS DEL INFORME  (edita aquí nombres, roles, necesidades y conflictos)
# ----------------------------------------------------------------------------
ZONES = [
    # nombre, inicio, fin, color de pared, color de zócalo, color de piso
    dict(name="Admisión", x0=0,    x1=560,  wall=(226, 238, 242), dado=(176, 208, 218), floor=(196, 214, 220)),
    dict(name="Triaje",             x0=560,  x1=1120, wall=(214, 240, 228), dado=(150, 205, 185), floor=(190, 222, 208)),
    dict(name="Consultorio",        x0=1120, x1=1760, wall=(250, 240, 214), dado=(222, 196, 140), floor=(232, 214, 176)),
    dict(name="Farmacia",           x0=1760, x1=2400, wall=(228, 240, 218), dado=(150, 196, 130), floor=(200, 224, 186)),
    dict(name="Dirección · DIRESA", x0=2400, x1=2960, wall=(244, 230, 232), dado=(176, 110, 124), floor=(222, 200, 204)),
]

# Los 8 stakeholders de la Tabla 7 del informe (2.4 Matriz de poder/interés).
# name = encargado · role = stakeholder · poder / interes / cuadrante = Tabla 7
# actividad: lo que hace el personaje en el centro de salud
#   (telefono, teclea, inspecciona, pasea, archiva, signos, acomoda, baila)
# need: lo que necesita (para el capítulo de requisitos) · says + conflict: Tablas 8, 9 y 10
# kind: aspecto del muñequito de prueba (solo si falta su PNG)
NPCS = [
    dict(id="arian",     x=2760, name="Sr. Arian Juan de Dios", role="Administración",
         poder="Alto", interes="Alto", cuadrante="Gestionar de cerca", actividad="telefono",
         need="Decidir qué 2 de los 5 módulos se priorizan",
         body=(122, 34, 48), accent=(75, 22, 32), kind="suit"),
    dict(id="leonidas",  x=1560, name="Ing. Leonidas Paredes", role="Equipo de TI",
         poder="Alto", interes="Alto", cuadrante="Gestionar de cerca", actividad="teclea",
         need="Seguridad de los datos de salud (Ley 29733)",
         body=(52, 58, 70), accent=(30, 34, 44), kind="suit", conflict="c3",
         says="¡Los datos de salud no pueden quedar expuestos!"),
    dict(id="carmen",    x=2400, name="Sra. Carmen Ochoa", role="MINSA",
         poder="Alto", interes="Medio", cuadrante="Mantener satisfecho", actividad="inspecciona",
         need="Cumplir la NTS 139 de historias clínicas",
         body=(70, 74, 96), accent=(46, 48, 64), kind="suit", conflict="c1",
         says="¡La norma no permite borrar registros!"),
    dict(id="jeremy",    x=1330, name="Dr. Jeremy Armas", role="Médico general",
         poder="Bajo", interes="Alto", cuadrante="Mantener informado", actividad="pasea",
         need="Registrar la atención y el diagnóstico CIE-10 rápido",
         body=(238, 241, 241), accent=(154, 167, 167), kind="doctor", conflict="c1",
         says="¡Necesito corregir rápido, en 5 clics!"),
    dict(id="mariajose", x=300,  name="Sra. María José", role="Personal de admisión",
         poder="Bajo", interes="Alto", cuadrante="Mantener informado", actividad="archiva",
         need="Abrir la historia con DNI o con un código temporal",
         body=(138, 96, 178), accent=(104, 70, 140), kind="normal"),
    dict(id="sara",      x=840,  name="Sra. Sara Acuy", role="Enfermería",
         poder="Bajo", interes="Alto", cuadrante="Mantener informado", actividad="signos",
         need="Registrar los signos vitales en el triaje",
         body=(47, 158, 143), accent=(30, 106, 96), kind="nurse", conflict="c3",
         says="¡No quiero perder lo registrado si se corta la conexión!"),
    dict(id="patroclo",  x=1980, name="Sr. Patroclo Suarez", role="Técnico de farmacia",
         poder="Bajo", interes="Alto", cuadrante="Mantener informado", actividad="acomoda",
         need="Dispensar las recetas sin el cuaderno",
         body=(79, 143, 63), accent=(47, 92, 38), kind="apron", conflict="c2",
         says="¡Cada salida debe descontarse del stock!"),
    dict(id="yasuri",    x=2200, name="Yasuri Yamileth", role="Pacientes (representante)",
         poder="Bajo", interes="Bajo", cuadrante="Monitorear", actividad="baila",
         need="Ser atendida sin demoras",
         body=(226, 168, 52), accent=(160, 110, 30), kind="normal", conflict="c2",
         says="¡No queremos hacer cola!"),
]

# Conflictos de la sección 2.5 (Tablas 8, 9 y 10). En el Capítulo 1 están apagados.
CONFLICTS = {
    "c1": dict(members=("jeremy", "carmen"),
               label="Médicos vs. Administración/MINSA",
               resolution="Resuelto: Inmutabilidad + Adenda Ágil (4.85, consenso)"),
    "c2": dict(members=("patroclo", "yasuri"),
               label="Farmacia vs. Pacientes/Médicos",
               resolution="Resuelto: Cola virtual, despacho en 1 clic (4.80, consenso)"),
    "c3": dict(members=("sara", "leonidas"),
               label="Médicos/Enfermería vs. Equipo TI/Administración",
               resolution="Resuelto: Autoguardado local cada 30 s, cifrado (4.20, consenso)"),
}

# ----------------------------------------------------------------------------
# HOSPITAL NUEVO: plano visto desde arriba + salas de perfil
# ----------------------------------------------------------------------------
PLANO_IMG = "assets/hospital_plano.png"           # el dibujo del hospital
PLANO_COL = "assets/hospital_colisiones.png"      # dónde se puede caminar (blanco) y dónde no (negro)
MAP_START = (296, 510)    # dónde aparece tu personaje al entrar (esquina de su dibujo de 32x32)
MAP_SPEED = 1.5           # velocidad en el plano
CONFLICT_RADIUS = 190     # a qué distancia del medio de dos stakeholders se ve su discusión

# color de la zona de puerta en hospital_colisiones.png  ->  sala a la que lleva
DOOR_COLORS = {
    (255, 0, 0): "admin",
    (255, 128, 0): "consultorio",
    (255, 255, 0): "triaje",
    (0, 200, 0): "admision",
    (0, 200, 255): "direccion",
    (0, 0, 255): "farmacia",
    (200, 0, 255): "espera",
    (255, 0, 160): "reuniones",
}

# cada sala: nombre, stakeholder que vive ahí, dónde está parado en el plano (map_pos)
# y dónde está parado dentro de la sala de perfil (x)
SALAS = {
    "admision":    dict(name="Admisión",              npc="mariajose", map_pos=(64, 434),  x=284),
    "triaje":      dict(name="Triaje",                npc="sara",      map_pos=(236, 256), x=236),
    "consultorio": dict(name="Consultorio",           npc="jeremy",    map_pos=(266, 64),  x=222),
    "admin":       dict(name="Sistemas · TI",         npc="leonidas",  map_pos=(84, 60),   x=176),
    "farmacia":    dict(name="Farmacia",              npc="patroclo",  map_pos=(560, 266), x=286),
    "espera":      dict(name="Sala de espera",        npc="yasuri",    map_pos=(556, 476), x=258),
    "direccion":   dict(name="Administración",        npc="arian",     map_pos=(444, 44),  x=228),
    "reuniones":   dict(name="Sala de reuniones",     npc="carmen",    map_pos=(28, 212),  x=140),
}

# ----------------------------------------------------------------------------
# CAPÍTULOS (se eligen en el buzón que está a la izquierda del centro de salud)
# Siguen las escenas del guion de sustentación.
# ----------------------------------------------------------------------------
CAPITULOS = [
    dict(titulo="El centro de salud de papel", mision="Conoce a los 8 stakeholders",
         logro="Conociendo a los stakeholders"),
    dict(titulo="Las decisiones del equipo", mision="Prioriza los módulos y resuelve 3 conflictos",
         logro="Decisiones con criterio"),
    dict(titulo="Sigue el hilo", mision="Sigue el hilo del RF-001 por 4 puertas",
         logro="Todo está conectado"),
]
BUZON_X = 76                         # dónde está el buzón en la calle (centro, en píxeles internos)
SALIDA_MAPA = (268, 550, 356, 560)   # zona de la puerta de entrada en el plano (x1, y1, x2, y2) para salir a la calle

# ----------------------------------------------------------------------------
# Utilidades de dibujo pixel art
# ----------------------------------------------------------------------------
def box(s, c, x, y, w, h):
    pygame.draw.rect(s, c, (int(x), int(y), int(w), int(h)))


def obox(s, c, x, y, w, h, o):
    box(s, o, x - 1, y - 1, w + 2, h + 2)
    box(s, c, x, y, w, h)


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


_pixfont = {}


def pixel_text(s, text, cx, y, color, size=11, shadow=None):
    if size not in _pixfont:
        _pixfont[size] = pygame.font.Font(None, size)
    f = _pixfont[size]
    if shadow:
        im = f.render(text, False, shadow)
        s.blit(im, (cx - im.get_width() // 2 + 1, y + 1))
    im = f.render(text, False, color)
    s.blit(im, (cx - im.get_width() // 2, y))


def cross(s, c, cx, cy, r, t):
    box(s, c, cx - t // 2, cy - r, t, 2 * r)
    box(s, c, cx - r, cy - t // 2, 2 * r, t)


def window(s, x, y, w, h, sky=(170, 215, 235)):
    obox(s, (60, 150, 160), x, y, w, h, (40, 100, 110))
    box(s, sky, x + 2, y + 2, w - 4, h - 4)
    box(s, (210, 240, 248), x + 2, y + 2, w - 4, 3)
    box(s, (60, 150, 160), x + w // 2 - 1, y + 2, 2, h - 4)
    box(s, (60, 150, 160), x + 2, y + h // 2 - 1, w - 4, 2)


def plant(s, x, y):
    obox(s, (190, 110, 70), x, y - 12, 14, 12, (120, 60, 40))
    for dx, dy, r in ((-2, -22, 6), (7, -26, 7), (14, -20, 6), (3, -17, 5)):
        pygame.draw.circle(s, (70, 150, 80), (x + dx + 4, y + dy), r)
        pygame.draw.circle(s, (110, 190, 110), (x + dx + 2, y + dy - 2), max(2, r - 3))


def sign(s, x, y, text, color=(40, 110, 130), w=None):
    w = w or (len(text) * 6 + 14)
    obox(s, color, x - w // 2, y, w, 14, shade(color, 0.55))
    box(s, shade(color, 1.25), x - w // 2 + 1, y + 1, w - 2, 1)
    pixel_text(s, text, x, y + 3, (245, 250, 250), 13)
    box(s, (90, 90, 90), x - w // 2 + 6, y - 6, 1, 6)
    box(s, (90, 90, 90), x + w // 2 - 7, y - 6, 1, 6)


# ----------------------------------------------------------------------------
# Fondo: se dibuja UNA vez en una imagen larga
# ----------------------------------------------------------------------------
def draw_exterior(s):
    """Escena de afuera: una sola pantalla (el hospital se dibuja aparte, con tu PNG)."""
    x0, x1 = 0, W
    for y in range(0, GROUND, 4):
        box(s, lerp((118, 190, 232), (198, 228, 244), y / GROUND), x0, y, x1 - x0, 4)
    for cx, cy in ((24, 30), (150, 18), (300, 40)):
        for dx, dy, w, h in ((0, 4, 34, 8), (6, 0, 22, 8), (22, 2, 22, 8)):
            box(s, (250, 252, 255), cx + dx, cy + dy, w, h)
            box(s, (222, 238, 248), cx + dx, cy + dy + h - 2, w, 2)
    for bx, bw, bh in ((0, 40, 60), (46, 30, 82), (84, 44, 52), (230, 34, 70), (270, 40, 56), (318, 30, 84), (352, 40, 60)):
        box(s, (160, 190, 212), bx, GROUND - bh, bw, bh)
        for wy in range(GROUND - bh + 6, GROUND - 6, 12):
            for wx in range(bx + 5, bx + bw - 6, 10):
                box(s, (190, 214, 230), wx, wy, 4, 5)
    def tree(tx):
        box(s, (120, 80, 50), tx - 3, GROUND - 40, 6, 40)
        for dx, dy, r in ((-14, -54, 14), (12, -58, 15), (0, -70, 14), (-4, -46, 12), (14, -44, 11)):
            pygame.draw.circle(s, (56, 130, 76), (tx + dx, GROUND + dy), r)
        for dx, dy, r in ((-16, -58, 6), (10, -62, 6), (0, -74, 6)):
            pygame.draw.circle(s, (100, 180, 104), (tx + dx, GROUND + dy), r)
    tree(352)
    for bx in (14, 66, 318, 372):
        pygame.draw.circle(s, (66, 150, 86), (bx, GROUND - 5), 9)
        pygame.draw.circle(s, (110, 190, 112), (bx - 3, GROUND - 8), 4)
    # banca (derecha)
    box(s, (140, 100, 70), 300, GROUND - 14, 34, 4)
    box(s, (140, 100, 70), 300, GROUND - 22, 34, 3)
    box(s, (90, 70, 50), 303, GROUND - 10, 3, 10)
    box(s, (90, 70, 50), 328, GROUND - 10, 3, 10)
    # poste de luz (izquierda)
    box(s, (70, 76, 84), 40, GROUND - 70, 3, 70)
    obox(s, (255, 236, 150), 35, GROUND - 78, 13, 8, (70, 76, 84))
    sign(s, 42, 100, "BIENVENIDO", (60, 140, 110), w=76)
    # vereda y calle
    box(s, (206, 206, 212), x0, GROUND, x1 - x0, 12)
    for vx in range(x0, x1, 24):
        box(s, (176, 176, 184), vx, GROUND + 2, 1, 10)
    box(s, (150, 150, 158), x0, GROUND + 12, x1 - x0, 2)
    box(s, (92, 96, 106), x0, GROUND + 14, x1 - x0, H - GROUND - 14)
    for vx in range(x0 + 10, x1, 56):
        box(s, (236, 220, 120), vx, GROUND + 22, 26, 3)

def _nube(s, x, y, w, h):
    """nube de píxeles: cuerpo + bultos arriba + sombra abajo"""
    box(s, (232, 242, 250), x, y + h // 2, w, h // 2)
    for bx, bw, bh in ((w * 0.10, w * 0.34, h * 0.75), (w * 0.34, w * 0.40, h * 1.0), (w * 0.62, w * 0.30, h * 0.65)):
        box(s, (250, 253, 255), x + int(bx), y + h - int(bh), int(bw), int(bh))
    box(s, (206, 224, 240), x, y + h - 3, w, 3)
    box(s, (250, 253, 255), x + 2, y + h // 2, w - 4, 2)


def _arbol(s, x, base, r):
    """árbol con contorno oscuro y dos tonos de verde"""
    box(s, (92, 60, 44), x - 3, base - r - 2, 6, r + 2)
    box(s, (130, 90, 62), x - 2, base - r - 2, 2, r + 2)
    puntos = ((0, -2.2 * r, 0.95 * r), (-0.8 * r, -1.5 * r, 0.8 * r), (0.8 * r, -1.5 * r, 0.8 * r), (0, -1.1 * r, 0.9 * r))
    for dx, dy, rr in puntos:
        pygame.draw.circle(s, (28, 70, 60), (int(x + dx), int(base + dy)), int(rr) + 1)
    for dx, dy, rr in puntos:
        pygame.draw.circle(s, (58, 140, 92), (int(x + dx), int(base + dy)), int(rr))
    for dx, dy, rr in puntos:
        pygame.draw.circle(s, (96, 186, 118), (int(x + dx - rr * 0.25), int(base + dy - rr * 0.3)), max(2, int(rr * 0.55)))


def _farola(s, x, base):
    box(s, (40, 56, 70), x - 1, base - 60, 3, 60)
    box(s, (40, 56, 70), x - 5, base - 3, 11, 3)
    box(s, (40, 56, 70), x - 1, base - 64, 9, 3)
    obox(s, (255, 240, 170), x + 4, base - 62, 7, 6, (40, 56, 70))
    box(s, (255, 252, 224), x + 5, base - 61, 3, 2)


def _seto(s, x, y, w, flores=True):
    obox(s, (64, 150, 90), x, y, w, 9, (28, 84, 64))
    box(s, (104, 190, 120), x, y, w, 2)
    for i in range(0, w - 3, 5):
        box(s, (44, 120, 80), x + i + 2, y + 5, 2, 2)
    if flores:
        cols = ((240, 110, 130), (250, 220, 90), (250, 250, 250))
        for i in range(2, w - 2, 7):
            box(s, cols[(i // 7) % 3], x + i, y + 1 + (i % 3), 2, 2)


def _reja(s, x0, x1, base):
    for x in range(x0, x1, 5):
        box(s, (250, 250, 246), x, base - 14, 3, 14)
        box(s, (190, 200, 210), x + 2, base - 14, 1, 14)
        box(s, (250, 250, 246), x, base - 16, 3, 1)
    box(s, (250, 250, 246), x0, base - 10, x1 - x0, 2)
    box(s, (190, 200, 210), x0, base - 8, x1 - x0, 1)


def _ambulancia(s, x, base):
    """ambulancia chiquita (dibujo propio) mirando a la izquierda"""
    ol = (34, 50, 70)
    obox(s, (248, 250, 252), x, base - 36, 62, 30, ol)                 # carrocería
    obox(s, (248, 250, 252), x - 16, base - 24, 18, 18, ol)            # trompa
    box(s, (200, 214, 226), x, base - 12, 62, 6)
    box(s, (214, 60, 70), x, base - 20, 62, 4)                         # franja roja
    obox(s, (130, 200, 224), x - 12, base - 34, 12, 12, ol)           # parabrisas
    box(s, (200, 238, 250), x - 11, base - 33, 4, 3)
    obox(s, (130, 200, 224), x + 8, base - 32, 12, 9, ol)             # ventana
    box(s, (214, 60, 70), x + 36, base - 31, 5, 15)                    # cruz
    box(s, (214, 60, 70), x + 31, base - 26, 15, 5)
    obox(s, (230, 70, 80), x + 22, base - 40, 12, 4, ol)              # sirena
    box(s, (130, 190, 255), x + 22, base - 40, 4, 4)
    box(s, (255, 230, 120), x - 16, base - 14, 4, 4)                   # faro
    for wx in (x - 6, x + 44):
        pygame.draw.circle(s, ol, (wx + 6, base - 4), 8)
        pygame.draw.circle(s, (58, 64, 76), (wx + 6, base - 4), 6)
        pygame.draw.circle(s, (190, 198, 210), (wx + 6, base - 4), 3)
    box(s, (0, 0, 0), x - 17, base + 3, 82, 0)


def draw_exterior(s):
    """Afueras del hospital: cielo, ciudad, árboles, jardín, vereda y calle (una sola pantalla)."""
    # cielo con bandas
    for y in range(0, GROUND, 4):
        box(s, lerp((96, 168, 222), (204, 232, 246), y / GROUND), 0, y, W, 4)
    pygame.draw.circle(s, (255, 244, 190), (330, 34), 15)
    pygame.draw.circle(s, (255, 250, 220), (330, 34), 10)
    _nube(s, 18, 22, 52, 16)
    _nube(s, 118, 12, 40, 12)
    _nube(s, 250, 56, 60, 16)
    _nube(s, 84, 60, 34, 10)
    # ciudad lejana (dos planos)
    for bx, bw, bh in ((2, 30, 56), (30, 26, 76), (54, 34, 48), (92, 22, 64), (270, 30, 62), (298, 24, 82), (320, 34, 54), (352, 32, 70)):
        box(s, (166, 200, 224), bx, GROUND - 14 - bh, bw, bh)
    for bx, bw, bh in ((0, 26, 40), (24, 34, 58), (60, 22, 36), (84, 28, 50), (284, 28, 46), (310, 30, 64), (338, 24, 42), (360, 24, 58)):
        box(s, (132, 176, 206), bx, GROUND - 14 - bh, bw, bh)
        for wy in range(GROUND - 14 - bh + 5, GROUND - 22, 9):
            for wx in range(bx + 4, bx + bw - 5, 8):
                box(s, (206, 230, 244), wx, wy, 3, 4)
    # césped
    box(s, (92, 176, 104), 0, GROUND - 22, W, 22)
    for gy in range(GROUND - 22, GROUND, 4):
        box(s, (84, 164, 96), 0, gy + 2, W, 1)
    for gx in range(3, W, 9):
        box(s, (122, 204, 124), gx, GROUND - 20 + (gx * 7) % 14, 2, 1)
    # árboles y rejas a los lados del hospital
    _arbol(s, 28, GROUND - 14, 15)
    _arbol(s, 354, GROUND - 14, 14)
    _arbol(s, 66, GROUND - 14, 10)
    _reja(s, 8, 50, GROUND - 3)
    _reja(s, 322, 376, GROUND - 3)
    _seto(s, 10, GROUND - 12, 36)
    _seto(s, 326, GROUND - 12, 44)
    # vereda
    box(s, (206, 208, 216), 0, GROUND, W, 14)
    for vx in range(0, W, 24):
        box(s, (176, 180, 192), vx, GROUND + 1, 1, 13)
    box(s, (226, 228, 234), 0, GROUND, W, 1)
    box(s, (150, 154, 168), 0, GROUND + 12, W, 2)
    # elementos de la vereda
    _farola(s, 52, GROUND + 2)
    _farola(s, 330, GROUND + 2)
    obox(s, (140, 100, 70), 130 - 100 + 100, GROUND - 14, 0, 0, (0, 0, 0)) if False else None
    # banca (izquierda)
    box(s, (150, 108, 76), 14, GROUND - 12, 30, 4)
    box(s, (150, 108, 76), 14, GROUND - 18, 30, 3)
    box(s, (92, 66, 50), 16, GROUND - 8, 3, 8)
    box(s, (92, 66, 50), 39, GROUND - 8, 3, 8)
    # ambulancia (derecha)
    _ambulancia(s, 312, GROUND + 3)
    # cartel de bienvenida
    sign(s, 42, 96, "BIENVENIDO", (60, 140, 110), w=76)
    # calle
    box(s, (92, 96, 106), 0, GROUND + 14, W, H - GROUND - 14)
    box(s, (120, 124, 134), 0, GROUND + 14, W, 2)
    for vx in range(10, W, 56):
        box(s, (236, 220, 120), vx, GROUND + 22, 26, 3)


def draw_interior_base(s, z):
    x0, x1 = z["x0"], z["x1"]
    w = x1 - x0
    box(s, z["wall"], x0, 0, w, GROUND)
    # techo con luces
    box(s, (240, 240, 236), x0, 0, w, 12)
    box(s, (206, 210, 210), x0, 12, w, 2)
    for lx in range(x0 + 40, x1 - 40, 112):
        obox(s, (255, 252, 220), lx, 2, 48, 6, (190, 190, 170))
    # zócalo (dado) y riel
    box(s, z["dado"], x0, 128, w, GROUND - 128)
    box(s, shade(z["dado"], 1.25), x0, 128, w, 3)
    box(s, shade(z["dado"], 0.8), x0, 131, w, 1)
    for lx in range(x0, x1, 32):
        box(s, shade(z["dado"], 0.9), lx, 132, 1, GROUND - 132)
    box(s, shade(z["dado"], 0.7), x0, GROUND - 5, w, 5)
    # piso
    box(s, z["floor"], x0, GROUND, w, H - GROUND)
    for ty in range(GROUND, H, 14):
        box(s, shade(z["floor"], 0.88), x0, ty, w, 1)
    for i, tx in enumerate(range(x0, x1, 28)):
        box(s, shade(z["floor"], 0.88), tx, GROUND, 1, H - GROUND)
        box(s, shade(z["floor"], 1.08), tx + 1, GROUND + 1, 8, 1)
    box(s, shade(z["floor"], 0.7), x0, GROUND, w, 2)
    # borde izquierdo (marco de puerta entre zonas)
    box(s, shade(z["wall"], 0.8), x0, 0, 4, GROUND)


def props_triaje(s, x0):
    sign(s, x0 + 90, 28, "TRIAJE", (40, 150, 130), w=60)
    # camilla
    obox(s, (230, 236, 240), x0 + 40, GROUND - 38, 64, 10, (120, 130, 140))
    box(s, (120, 190, 200), x0 + 42, GROUND - 40, 60, 4)
    box(s, (250, 250, 250), x0 + 42, GROUND - 44, 16, 6)
    box(s, (130, 140, 150), x0 + 46, GROUND - 28, 4, 28)
    box(s, (130, 140, 150), x0 + 96, GROUND - 28, 4, 28)
    # cortina
    for i in range(0, 40, 8):
        box(s, (150, 215, 205), x0 + 118 + i, 40, 8, 88)
        box(s, (120, 190, 180), x0 + 118 + i, 40, 1, 88)
    box(s, (110, 120, 130), x0 + 112, 38, 52, 3)
    # reloj
    pygame.draw.circle(s, (60, 60, 60), (x0 + 250, 52), 12)
    pygame.draw.circle(s, (250, 250, 245), (x0 + 250, 52), 10)
    box(s, (40, 40, 40), x0 + 250, 46, 1, 6)
    box(s, (40, 40, 40), x0 + 250, 52, 5, 1)
    # balanza con tallímetro
    box(s, (140, 150, 158), x0 + 330, GROUND - 76, 3, 76)
    for ty in range(GROUND - 72, GROUND - 6, 8):
        box(s, (60, 60, 60), x0 + 333, ty, 4, 1)
    obox(s, (210, 214, 218), x0 + 318, GROUND - 8, 30, 8, (100, 106, 112))
    # tensiómetro en la pared
    obox(s, (240, 244, 246), x0 + 390, 70, 26, 20, (110, 120, 130))
    box(s, (120, 200, 160), x0 + 394, 74, 18, 8)
    box(s, (220, 70, 80), x0 + 398, 78, 2, 2)
    # póster corazón
    obox(s, (250, 245, 240), x0 + 450, 54, 34, 44, (160, 150, 140))
    for hx, hy in ((460, 70), (470, 70)):
        pygame.draw.circle(s, (220, 60, 80), (x0 + hx, hy), 5)
    pygame.draw.polygon(s, (220, 60, 80), [(x0 + 454, 73), (x0 + 476, 73), (x0 + 465, 88)])
    # suero
    box(s, (150, 156, 164), x0 + 500, GROUND - 70, 2, 70)
    box(s, (150, 156, 164), x0 + 494, GROUND - 70, 14, 2)
    obox(s, (200, 230, 245), x0 + 494, GROUND - 66, 8, 14, (110, 140, 160))
    plant(s, x0 + 536, GROUND)


def props_consultorio(s, x0):
    sign(s, x0 + 110, 28, "CONSULTORIO", (200, 150, 60), w=82)
    # diplomas
    for i in range(3):
        obox(s, (250, 244, 224), x0 + 40 + i * 24, 58, 18, 24, (150, 110, 60))
        box(s, (200, 60, 60), x0 + 46 + i * 24, 72, 6, 2)
    # camilla de examen
    obox(s, (96, 150, 170), x0 + 20, GROUND - 34, 70, 12, (50, 90, 110))
    box(s, (240, 248, 250), x0 + 20, GROUND - 38, 70, 5)
    box(s, (130, 140, 150), x0 + 28, GROUND - 22, 4, 22)
    box(s, (130, 140, 150), x0 + 78, GROUND - 22, 4, 22)
    # póster anatomía
    obox(s, (248, 244, 232), x0 + 150, 52, 40, 56, (150, 130, 100))
    pygame.draw.circle(s, (230, 160, 150), (x0 + 170, 66), 6)
    box(s, (210, 120, 110), x0 + 164, 74, 12, 22)
    box(s, (210, 120, 110), x0 + 158, 76, 6, 3)
    box(s, (210, 120, 110), x0 + 176, 76, 6, 3)
    # ventana
    window(s, x0 + 235, 46, 56, 56)
    # escritorio con computadora
    obox(s, (150, 104, 70), x0 + 330, GROUND - 38, 100, 10, (90, 60, 40))
    box(s, (120, 80, 55), x0 + 336, GROUND - 28, 8, 28)
    box(s, (120, 80, 55), x0 + 414, GROUND - 28, 8, 28)
    obox(s, (40, 50, 60), x0 + 370, GROUND - 66, 34, 24, (20, 26, 34))
    box(s, (110, 200, 230), x0 + 373, GROUND - 63, 28, 18)
    box(s, (60, 140, 170), x0 + 376, GROUND - 60, 14, 2)
    box(s, (60, 140, 170), x0 + 376, GROUND - 56, 20, 2)
    box(s, (40, 50, 60), x0 + 384, GROUND - 42, 6, 4)
    obox(s, (230, 230, 230), x0 + 360, GROUND - 40, 26, 3, (130, 130, 130))
    # silla
    box(s, (60, 70, 90), x0 + 440, GROUND - 34, 18, 6)
    box(s, (60, 70, 90), x0 + 456, GROUND - 52, 4, 24)
    box(s, (50, 50, 60), x0 + 446, GROUND - 28, 3, 28)
    plant(s, x0 + 590, GROUND)


def props_farmacia(s, x0):
    sign(s, x0 + 100, 28, "FARMACIA", (50, 160, 90), w=64)
    cross(s, (60, 180, 100), x0 + 100, 56, 11, 7)
    # estantes de medicinas al fondo (toda la pared)
    for sx in range(x0 + 150, x0 + 560, 52):
        obox(s, (200, 206, 212), sx, 40, 46, 84, (120, 128, 136))
        for ry in (40, 62, 84, 106):
            box(s, (140, 148, 156), sx, ry + 20, 46, 2)
            for k in range(5):
                col = [(220, 90, 90), (90, 150, 220), (240, 200, 80), (110, 190, 120), (200, 140, 210)][(k + sx // 7 + ry) % 5]
                bh = 10 + ((k * 3 + ry) % 6)
                box(s, col, sx + 3 + k * 8, ry + 20 - bh, 6, bh)
    # ventanilla de dispensación
    obox(s, (170, 120, 80), x0 + 180, GROUND - 52, 150, 12, (100, 66, 42))
    box(s, (130, 90, 60), x0 + 184, GROUND - 40, 142, 40)
    box(s, (150, 106, 72), x0 + 184, GROUND - 40, 142, 2)
    for px_ in range(x0 + 192, x0 + 320, 22):
        box(s, (116, 78, 52), px_, GROUND - 34, 16, 28)
    obox(s, (200, 232, 240), x0 + 190, GROUND - 82, 130, 30, (100, 130, 140))
    box(s, (240, 250, 252), x0 + 196, GROUND - 78, 22, 3)
    box(s, (240, 250, 252), x0 + 222, GROUND - 78, 6, 3)
    sign(s, x0 + 255, GROUND - 100, "DESPACHO", (50, 150, 90), w=62)
    # banca de espera
    box(s, (90, 130, 180), x0 + 370, GROUND - 22, 80, 8)
    box(s, (70, 106, 150), x0 + 370, GROUND - 38, 80, 6)
    box(s, (60, 66, 80), x0 + 376, GROUND - 14, 3, 14)
    box(s, (60, 66, 80), x0 + 442, GROUND - 14, 3, 14)
    # ticket / turno
    obox(s, (30, 36, 44), x0 + 340, 84, 22, 14, (10, 12, 16))
    pixel_text(s, "37", x0 + 351, 87, (255, 120, 80), 12)


def props_direccion(s, x0):
    sign(s, x0 + 100, 28, "DIRECCIÓN", (130, 50, 66), w=70)
    # ventanal con ciudad
    obox(s, (70, 100, 130), x0 + 20, 44, 120, 78, (40, 60, 80))
    box(s, (176, 220, 240), x0 + 23, 47, 114, 72)
    for bx_, bh, bw_ in ((26, 36, 16), (46, 50, 14), (64, 28, 18), (88, 44, 14), (108, 32, 20)):
        box(s, (120, 154, 184), x0 + bx_, 119 - bh, bw_, bh)
    box(s, (70, 100, 130), x0 + 79, 47, 2, 72)
    box(s, (70, 100, 130), x0 + 23, 82, 114, 2)
    # bandera (rojo-blanco-rojo)
    box(s, (140, 110, 70), x0 + 176, 52, 2, GROUND - 52)
    box(s, (210, 40, 50), x0 + 178, 54, 10, 30)
    box(s, (250, 250, 250), x0 + 188, 54, 10, 30)
    box(s, (210, 40, 50), x0 + 198, 54, 10, 30)
    # pizarra con gráfico
    obox(s, (250, 250, 248), x0 + 230, 52, 90, 58, (120, 100, 80))
    for i, bh in enumerate((16, 28, 22, 40, 34)):
        box(s, (200, 80, 90), x0 + 242 + i * 14, 104 - bh, 9, bh)
    box(s, (60, 60, 60), x0 + 238, 104, 76, 1)
    # escritorio grande
    obox(s, (120, 70, 60), x0 + 410, GROUND - 40, 120, 12, (70, 40, 34))
    box(s, (92, 52, 44), x0 + 418, GROUND - 28, 104, 28)
    box(s, (70, 40, 34), x0 + 418, GROUND - 28, 104, 2)
    obox(s, (40, 50, 60), x0 + 450, GROUND - 68, 34, 24, (20, 26, 34))
    box(s, (110, 200, 230), x0 + 453, GROUND - 65, 28, 18)
    plant(s, x0 + 538, GROUND)


def props_admision(s, x0):
    sign(s, x0 + 110, 28, "ADMISIÓN", (60, 120, 170), w=64)
    # marco de la puerta por donde se entra (lado izquierdo)
    obox(s, (60, 150, 160), x0 + 2, 40, 16, GROUND - 40, (40, 100, 110))
    box(s, (190, 235, 245), x0 + 5, 44, 10, GROUND - 48)
    # cartel con la historia clínica
    obox(s, (250, 245, 240), x0 + 40, 56, 34, 44, (160, 150, 140))
    box(s, (200, 70, 80), x0 + 48, 64, 18, 4)
    for i in range(4):
        box(s, (150, 150, 160), x0 + 48, 74 + i * 6, 18, 2)
    # reloj
    pygame.draw.circle(s, (60, 60, 60), (x0 + 150, 52), 12)
    pygame.draw.circle(s, (250, 250, 245), (x0 + 150, 52), 10)
    box(s, (40, 40, 40), x0 + 150, 46, 1, 6)
    box(s, (40, 40, 40), x0 + 150, 52, 5, 1)
    # mostrador de admisión con computadora
    obox(s, (214, 220, 226), x0 + 150, GROUND - 42, 120, 10, (120, 130, 140))
    box(s, (110, 160, 200), x0 + 156, GROUND - 32, 108, 32)
    box(s, (140, 190, 225), x0 + 156, GROUND - 32, 108, 2)
    obox(s, (40, 50, 60), x0 + 190, GROUND - 68, 34, 24, (20, 26, 34))
    box(s, (110, 200, 230), x0 + 193, GROUND - 65, 28, 18)
    box(s, (60, 140, 170), x0 + 196, GROUND - 62, 14, 2)
    # sala de espera
    box(s, (90, 130, 180), x0 + 360, GROUND - 22, 80, 8)
    box(s, (70, 106, 150), x0 + 360, GROUND - 38, 80, 6)
    box(s, (60, 66, 80), x0 + 366, GROUND - 14, 3, 14)
    box(s, (60, 66, 80), x0 + 432, GROUND - 14, 3, 14)
    window(s, x0 + 300, 46, 40, 44)
    plant(s, x0 + 470, GROUND)
    sign(s, x0 + 520, 60, "TRIAJE  >", (40, 150, 130), w=64)


def build_background():
    bg = pygame.Surface((WORLD_W, H))
    for z in ZONES:
        draw_interior_base(bg, z)
    props_admision(bg, ZONES[0]["x0"])
    props_triaje(bg, ZONES[1]["x0"])
    props_consultorio(bg, ZONES[2]["x0"])
    props_farmacia(bg, ZONES[3]["x0"])
    props_direccion(bg, ZONES[4]["x0"])
    return bg


def build_exterior():
    s = pygame.Surface((W, H))
    draw_exterior(s)
    return s


# ----------------------------------------------------------------------------
# Personajes
# ----------------------------------------------------------------------------
def make_npc_sprite(body, accent, kind):
    """Muñequito de prueba 32x32 mirando a la izquierda (como tu sprite)."""
    s = pygame.Surface((SPRITE, SPRITE), pygame.SRCALPHA)
    skin, dark = (240, 205, 165), (60, 40, 30)
    outline = (40, 30, 40)
    # piernas
    box(s, (50, 56, 80), 11, 25, 5, 6)
    box(s, (50, 56, 80), 17, 25, 5, 6)
    box(s, outline, 10, 30, 7, 2)
    box(s, outline, 16, 30, 7, 2)
    # cuerpo
    obox(s, body, 9, 13, 15, 13, outline)
    box(s, shade(body, 0.85), 9, 22, 15, 4)
    # brazos
    box(s, shade(body, 0.9), 7, 15, 3, 9)
    box(s, shade(body, 0.9), 23, 15, 3, 9)
    box(s, skin, 7, 23, 3, 2)
    box(s, skin, 23, 23, 3, 2)
    # cabeza
    obox(s, skin, 10, 2, 13, 12, outline)
    box(s, dark, 10, 2, 13, 4)
    box(s, dark, 21, 4, 2, 6)
    box(s, (20, 20, 30), 12, 8, 2, 2)     # ojo (mira a la izquierda)
    box(s, (20, 20, 30), 17, 8, 2, 2)
    box(s, (200, 120, 110), 13, 11, 4, 1)
    if kind == "doctor":
        box(s, (250, 250, 250), 9, 18, 15, 8)  # bata larga
        box(s, accent, 12, 14, 1, 7)
        box(s, accent, 15, 14, 1, 4)
        pygame.draw.circle(s, accent, (13, 22), 2, 1)
    elif kind == "nurse":
        obox(s, (250, 250, 250), 10, 0, 13, 4, outline)
        cross(s, (220, 60, 70), 16, 2, 1, 1)
        box(s, (250, 250, 250), 13, 14, 7, 12)
    elif kind == "suit":
        box(s, (250, 250, 250), 14, 13, 5, 7)
        box(s, (200, 50, 60), 16, 14, 1, 8)
        box(s, accent, 9, 13, 5, 13)
        box(s, accent, 19, 13, 5, 13)
    elif kind == "apron":
        box(s, (250, 250, 250), 12, 15, 9, 11)
        box(s, accent, 12, 15, 9, 1)
        box(s, (200, 60, 70), 15, 18, 3, 3)
    return s

def grow(im):
    if CHAR_SCALE == 1:
        return im
    return pygame.transform.scale(im, (int(im.get_width() * CHAR_SCALE), int(im.get_height() * CHAR_SCALE)))

def load_player_frames():
    frames = []
    for i in range(1, 5):
        im = pygame.image.load(res(f"assets/jugador_{i}.png")).convert_alpha()
        frames.append(grow(im))
    return frames


def load_npc_sprites():
    out = {}
    for n in NPCS:
        found = None
        for nombre in (f"npc_{n['id']}_izquierda.png", f"npc_{n['id']}.png"):
            p = res("assets/" + nombre)
            if os.path.exists(p):
                found = p
                break
        if found:
            out[n["id"]] = grow(pygame.image.load(found).convert_alpha())
        else:
            out[n["id"]] = grow(make_npc_sprite(n["body"], n["accent"], n["kind"]))
    return out

def load_map_sprites():
    """Tu personaje en el plano (32x32, sin agrandar): 4 direcciones x 4 cuadros de caminata."""
    out = {}
    for d in ("frente", "espalda", "izquierda", "derecha"):
        out[d] = [pygame.image.load(res(f"assets/jugador_{d}_{i}.png")).convert_alpha() for i in range(1, 5)]
    return out

def load_npc_front():
    """Los stakeholders de frente (32x32) para verlos en el plano."""
    out = {}
    for n in NPCS:
        p = res(f"assets/npc_{n['id']}_frente.png")
        if os.path.exists(p):
            out[n["id"]] = pygame.image.load(p).convert_alpha()
        else:
            out[n["id"]] = make_npc_sprite(n["body"], n["accent"], n["kind"])
    return out

# ----------------------------------------------------------------------------
# INTERFAZ (UI) EN PIXEL ART
# Todo se dibuja en 384x216 (igual que el mundo) y luego se amplía x3, así los
# marcos, los textos y los iconos quedan con píxeles nítidos.
# ----------------------------------------------------------------------------
UI_FONDO = (22, 30, 52)         # azul noche de los paneles
UI_FONDO2 = (36, 48, 82)        # azul un poco más claro (franjas y brillos)
UI_LINEA = (8, 12, 24)          # contorno oscuro de todo
UI_ORO = (240, 180, 41)         # dorado de los bordes y títulos
UI_ORO_OSC = (150, 100, 24)
UI_CREMA = (251, 234, 208)      # texto principal
UI_GRIS = (140, 154, 184)       # texto secundario
UI_ROJO = (222, 92, 92)         # conflictos
UI_VERDE = (110, 200, 120)      # resuelto / identificado

# Letra pixel art de 5x7 (todo en mayúsculas). Cada letra = 7 filas separadas por coma.
_LETRAS = {
    "A": "01110,10001,10001,11111,10001,10001,10001", "B": "11110,10001,10001,11110,10001,10001,11110",
    "C": "01110,10001,10000,10000,10000,10001,01110", "D": "11110,10001,10001,10001,10001,10001,11110",
    "E": "11111,10000,10000,11110,10000,10000,11111", "F": "11111,10000,10000,11110,10000,10000,10000",
    "G": "01110,10001,10000,10111,10001,10001,01111", "H": "10001,10001,10001,11111,10001,10001,10001",
    "I": "01110,00100,00100,00100,00100,00100,01110", "J": "00111,00010,00010,00010,00010,10010,01100",
    "K": "10001,10010,10100,11000,10100,10010,10001", "L": "10000,10000,10000,10000,10000,10000,11111",
    "M": "10001,11011,10101,10101,10001,10001,10001", "N": "10001,11001,11001,10101,10011,10011,10001",
    "O": "01110,10001,10001,10001,10001,10001,01110", "P": "11110,10001,10001,11110,10000,10000,10000",
    "Q": "01110,10001,10001,10001,10101,10010,01101", "R": "11110,10001,10001,11110,10100,10010,10001",
    "S": "01111,10000,10000,01110,00001,00001,11110", "T": "11111,00100,00100,00100,00100,00100,00100",
    "U": "10001,10001,10001,10001,10001,10001,01110", "V": "10001,10001,10001,10001,10001,01010,00100",
    "W": "10001,10001,10001,10101,10101,11011,10001", "X": "10001,10001,01010,00100,01010,10001,10001",
    "Y": "10001,10001,01010,00100,00100,00100,00100", "Z": "11111,00001,00010,00100,01000,10000,11111",
    "0": "01110,10001,10011,10101,11001,10001,01110", "1": "00100,01100,00100,00100,00100,00100,01110",
    "2": "01110,10001,00001,00010,00100,01000,11111", "3": "11110,00001,00001,01110,00001,00001,11110",
    "4": "00010,00110,01010,10010,11111,00010,00010", "5": "11111,10000,11110,00001,00001,10001,01110",
    "6": "00110,01000,10000,11110,10001,10001,01110", "7": "11111,00001,00010,00100,01000,01000,01000",
    "8": "01110,10001,10001,01110,10001,10001,01110", "9": "01110,10001,10001,01111,00001,00010,01100",
    " ": "000,000,000,000,000,000,000", ".": "0,0,0,0,0,0,1", ",": "0,0,0,0,0,1,1", ":": "0,1,0,0,0,1,0",
    "!": "1,1,1,1,1,0,1", "¡": "1,0,1,1,1,1,1", "?": "01110,10001,00001,00010,00100,00000,00100",
    "¿": "00100,00000,00100,01000,10000,10001,01110", "/": "00001,00001,00010,00100,01000,10000,10000",
    "-": "000,000,000,111,000,000,000", "+": "000,000,010,111,010,000,000", "(": "01,10,10,10,10,10,01",
    ")": "10,01,01,01,01,01,10", "·": "0,0,0,1,0,0,0", "'": "1,1,0,0,0,0,0", "%": "10001,10010,00010,00100,01000,01001,10001",
}
LETRAS = {k: v.split(",") for k, v in _LETRAS.items()}
# letras con tilde: (letra base, tilde). La tilde se dibuja en 2 filas encima de la letra.
_TILDES = {"agudo": ("00010", "00100"), "tilde": ("01001", "10010"), "diere": ("01010", "00000")}
ACENTOS = {"Á": ("A", "agudo"), "É": ("E", "agudo"), "Í": ("I", "agudo"), "Ó": ("O", "agudo"),
           "Ú": ("U", "agudo"), "Ñ": ("N", "tilde"), "Ü": ("U", "diere")}
_CAMBIOS = {"—": "-", "–": "-", "…": "...", "“": "'", "”": "'", '"': "'", "«": "'", "»": "'", "’": "'",
            "[": "(", "]": ")", "·": "·"}
_CACHE_TEXTO = {}


def _limpiar(texto):
    for a, b in _CAMBIOS.items():
        texto = texto.replace(a, b)
    return texto.upper()


def ui_ancho(texto):
    """Ancho en píxeles de un texto con la letra pixel art."""
    total = 0
    for ch in _limpiar(texto):
        base = ACENTOS[ch][0] if ch in ACENTOS else ch
        total += len(LETRAS.get(base, LETRAS["?"])[0]) + 1
    return max(0, total - 1)


def ui_texto(texto, color, sombra=UI_LINEA):
    """Devuelve una imagen del texto (con sombra de 1 píxel). Se guarda en memoria para no redibujar."""
    clave = (texto, color, sombra)
    if clave in _CACHE_TEXTO:
        return _CACHE_TEXTO[clave]
    texto = _limpiar(texto)
    s = pygame.Surface((ui_ancho(texto) + 2, 10), pygame.SRCALPHA)
    for col, dx, dy in ((sombra, 1, 1), (color, 0, 0)):
        if col is None:
            continue
        x = 0
        for ch in texto:
            base, tilde = ACENTOS.get(ch, (ch, None))
            g = LETRAS.get(base, LETRAS["?"])
            for j, fila in enumerate(g):
                for i, v in enumerate(fila):
                    if v == "1":
                        s.set_at((x + i + dx, 2 + j + dy), col)
            if tilde:
                for j, fila in enumerate(_TILDES[tilde]):
                    for i, v in enumerate(fila):
                        if v == "1" and i < len(g[0]):
                            s.set_at((x + i + dx, j + dy), col)
            x += len(g[0]) + 1
    _CACHE_TEXTO[clave] = s
    return s


def ui_partir(texto, ancho):
    """Parte un texto en líneas que no pasen de 'ancho' píxeles."""
    lineas, actual = [], ""
    for palabra in texto.split(" "):
        prueba = (actual + " " + palabra).strip()
        if ui_ancho(prueba) > ancho and actual:
            lineas.append(actual)
            actual = palabra
        else:
            actual = prueba
    if actual:
        lineas.append(actual)
    return lineas


def ui_cortar(texto, ancho):
    """Corta un texto con '...' si no cabe en 'ancho' píxeles."""
    if ui_ancho(texto) <= ancho:
        return texto
    while len(texto) > 1 and ui_ancho(texto + "...") > ancho:
        texto = texto[:-1]
    return texto.rstrip() + "..."


def ui_rect(s, color, x, y, w, h):
    if w > 0 and h > 0:
        pygame.draw.rect(s, color, (int(x), int(y), int(w), int(h)))


def ui_marco(s, x, y, w, h, borde=UI_ORO, fondo=UI_FONDO, brillo=True, sombra=True):
    """Marco pixel art: sombra, contorno oscuro con esquinas cortadas, borde de color y fondo con brillo."""
    x, y, w, h = int(x), int(y), int(w), int(h)
    if sombra:
        ui_rect(s, (0, 0, 0, 80), x + 1, y + 2, w, h)
    ui_rect(s, UI_LINEA, x + 1, y, w - 2, h)               # contorno (esquinas cortadas)
    ui_rect(s, UI_LINEA, x, y + 1, w, h - 2)
    ui_rect(s, borde, x + 2, y + 1, w - 4, h - 2)           # borde de color
    ui_rect(s, borde, x + 1, y + 2, w - 2, h - 4)
    ui_rect(s, fondo, x + 3, y + 2, w - 6, h - 4)           # fondo
    ui_rect(s, fondo, x + 2, y + 3, w - 4, h - 6)
    if brillo:
        ui_rect(s, tuple(min(255, c + 14) for c in fondo[:3]), x + 3, y + 2, w - 6, 1)   # brillo arriba
        ui_rect(s, tuple(max(0, c - 8) for c in fondo[:3]), x + 3, y + h - 3, w - 6, 1)  # sombra abajo
    for cx, cy in ((x + 2, y + 2), (x + w - 3, y + 2), (x + 2, y + h - 3), (x + w - 3, y + h - 3)):
        s.set_at((cx, cy), borde)                           # remaches en las esquinas


def ui_icono(s, x, y, filas, paleta):
    """Dibuja un icono hecho con letras: cada letra de 'filas' es un color de 'paleta' ('.' = nada)."""
    for j, fila in enumerate(filas):
        for i, ch in enumerate(fila):
            if ch in paleta:
                s.set_at((int(x) + i, int(y) + j), paleta[ch])


ICONO_OK = ["..LLLLL..", ".LGGGGGL.", "LGGGGGWGL", "LGGGGWWGL", "LGWGWWGGL", "LGGWWGGGL", "LGGGWGGGL", ".LGGGGGL.", "..LLLLL.."]
PAL_OK = {"L": UI_LINEA, "G": (70, 170, 100), "W": (255, 255, 255)}
ICONO_RAYO = ["....LLL.", "...LYYL.", "..LYYL..", ".LYYYL..", "LYYYYYYL", "LLLYYYL.", "..LYYL..", "..LYL...", "..LL...."]
PAL_RAYO = {"L": (120, 40, 30), "Y": (255, 214, 64)}
ICONO_ESTRELLA = ["....L....", "...LYL...", "...LYL...", "LLLLYLLLL", ".LYYYYYL.", "..LYYYL..", "..LYLYL..", ".LYL.LYL.", ".LL...LL."]
PAL_ESTRELLA = {"L": (120, 70, 20), "Y": (255, 214, 64)}


def ui_tecla(s, x, y, letra, abajo=False):
    """Tecla de teclado pixel art. Devuelve su ancho."""
    x, y = int(x), int(y) + (1 if abajo else 0)
    w = ui_ancho(letra) + 6
    ui_rect(s, UI_LINEA, x + 1, y, w - 2, 12)
    ui_rect(s, UI_LINEA, x, y + 1, w, 10)
    ui_rect(s, (170, 150, 120), x + 1, y + 9, w - 2, 2)          # canto de la tecla
    ui_rect(s, UI_CREMA, x + 1, y + 1, w - 2, 9)                 # cara de la tecla
    ui_rect(s, (255, 250, 238), x + 2, y + 1, w - 4, 1)
    s.blit(ui_texto(letra, UI_FONDO, None), (x + 3, y))
    return w


# --- iconos extra: logro, candado y colores de la matriz poder/interés ---
ICONO_TROFEO = ["LLLLLLLLL", "LYYYYYYYL", "LYWYYYYYL", "LLYYYYYLL", ".LYYYYYL.", "..LYYYL..", "...LYL...", "..LLYLL..", ".LYYYYYL.", ".LLLLLLL."]
PAL_TROFEO = {"L": (110, 66, 16), "Y": (255, 200, 60), "W": (255, 246, 190)}
ICONO_CANDADO = ["..LLL..", ".L...L.", ".L...L.", "LLLLLLL", "LGGGGGL", "LGGLGGL", "LGGLGGL", "LLLLLLL"]
PAL_CANDADO = {"L": UI_LINEA, "G": (150, 154, 170)}
COLOR_CUADRANTE = {"Gestionar de cerca": (255, 130, 115), "Mantener satisfecho": (255, 196, 90),
                   "Mantener informado": (120, 200, 255), "Monitorear": (160, 210, 160)}
NIVEL = {"Bajo": 1, "Medio": 2, "Alto": 3}


def ui_medidor(s, x, y, nivel):
    """3 barritas: cuántas están llenas según Bajo / Medio / Alto. Devuelve su ancho."""
    for i in range(3):
        ui_rect(s, UI_LINEA, x + i * 4, y, 4, 8)
        ui_rect(s, UI_ORO if i < NIVEL.get(nivel, 0) else (52, 64, 98), x + i * 4 + 1, y + 1, 2, 6)
    return 13


# --- partículas de los stakeholders (cada "X" es un píxel) ---
P_NOTA = ["..XX.", "..X.X", "..X..", "..X..", ".XX..", "XXX..", ".X..."]
P_CORAZON = ["XX.XX", "XXXXX", ".XXX.", "..X.."]
P_GOTA = [".X.", "XXX", "XXX", ".X."]
P_CHECK = ["....X", "...X.", "X.X..", ".X..."]
P_CERO = ["XXX", "X.X", "X.X", "X.X", "XXX"]
P_UNO = [".X.", "XX.", ".X.", ".X.", "XXX"]
P_PASTILLA = ["AABB"]
P_HOJA = ["AAAA", "ABBA", "AAAA", "ABBA", "AAAA"]
P_SELLO = [".AA.", "AAAA", ".AA.", "BBBB"]


def px_icono(s, x, y, filas, color, esc=1, color_b=None):
    """Dibuja un iconito de partículas con sombrita. 'A' usa color, 'B' usa color_b, 'X' usa color."""
    for j, fila in enumerate(filas):
        for i, ch in enumerate(fila):
            if ch in "XAB":
                c = color_b if (ch == "B" and color_b) else color
                ui_rect(s, (24, 24, 36), int(x) + i * esc + esc, int(y) + j * esc + esc, esc, esc)
                ui_rect(s, c, int(x) + i * esc, int(y) + j * esc, esc, esc)


def dibujar_buzon(s, x, base, t, nuevo):
    """Buzón pixel art (x = centro, base = suelo). Si hay capítulo nuevo, la banderita sube y sale un '!'."""
    x, base = int(x), int(base)
    ui_rect(s, (0, 0, 0, 60), x - 7, base - 1, 14, 3)                    # sombra en el suelo
    ui_rect(s, UI_LINEA, x - 2, base - 16, 4, 16)                         # poste
    ui_rect(s, (120, 96, 72), x - 1, base - 16, 2, 16)
    bx, by = x - 8, base - 29
    ui_rect(s, UI_LINEA, bx + 1, by, 14, 14)                              # caja (esquinas cortadas)
    ui_rect(s, UI_LINEA, bx, by + 1, 16, 12)
    ui_rect(s, (206, 58, 58), bx + 1, by + 1, 14, 12)
    ui_rect(s, (236, 96, 90), bx + 2, by + 1, 12, 2)                      # brillo de arriba
    ui_rect(s, (150, 36, 40), bx + 1, by + 11, 14, 2)                     # sombra de abajo
    ui_rect(s, UI_LINEA, bx + 4, by + 4, 8, 2)                            # ranura de las cartas
    ui_rect(s, (250, 246, 236), bx + 4, by + 7, 8, 4)                     # sobrecito blanco
    s.set_at((bx + 5, by + 8), (190, 60, 60))
    s.set_at((bx + 10, by + 8), (190, 60, 60))
    ui_rect(s, (190, 60, 60), bx + 6, by + 9, 4, 1)
    if nuevo:                                                             # banderita levantada
        ui_rect(s, UI_LINEA, bx + 16, by - 6, 2, 14)
        ui_rect(s, UI_LINEA, bx + 17, by - 7, 6, 6)
        ui_rect(s, (255, 214, 64), bx + 18, by - 6, 4, 4)
        dy = int(math.sin(t * 0.15) * 2)                                  # "!" que flota arriba
        ui_rect(s, UI_LINEA, x - 3, by - 16 + dy, 7, 12)
        ui_rect(s, (255, 214, 64), x - 2, by - 15 + dy, 5, 10)
        ui_rect(s, UI_LINEA, x, by - 14 + dy, 1, 5)
        ui_rect(s, UI_LINEA, x, by - 8 + dy, 1, 2)
    else:                                                                 # banderita abajo
        ui_rect(s, UI_LINEA, bx + 15, by + 5, 7, 3)
        ui_rect(s, (220, 190, 60), bx + 16, by + 6, 5, 1)
# ======================== FIN DEL BLOQUE B ========================

# ============================================================================
# CAPÍTULOS 2 Y 3: DATOS DEL INFORME (edita aquí los textos)
# ============================================================================
LETRAS.update({                                   # letras que faltaban
    ">": ["000", "100", "010", "001", "010", "100", "000"],
    "<": ["000", "001", "010", "100", "010", "001", "000"],
    "=": ["000", "000", "111", "000", "111", "000", "000"],
    "→": ["00000", "00100", "00010", "11111", "00010", "00100", "00000"],
    "≤": ["001", "010", "100", "010", "001", "000", "111"],
    "#": ["01010", "11111", "01010", "01010", "11111", "01010", "00000"],
})

# Capítulo 1: cartel "Lo que el caso no decía" (Tabla 2)
SUPUESTOS = [
    "No dice cuántos usuarios habrá → supusimos 50 al mismo tiempo (RNF-001).",
    "No dice cómo identificar al paciente → usamos el DNI (RF-001).",
    "No dice qué módulos van primero → priorizamos la Historia Clínica Electrónica y la Receta Electrónica.",
    "No dice qué catálogo de diagnósticos usar → adoptamos el CIE-10 (RF-004).",
]

# Capítulo 2: los 5 módulos y solo 2 monedas (Tablas 13 y 14, sección 2.7)
# ok = True si es uno de los 2 que entran en la primera fase
MODULOS = [
    dict(nombre="Historia Clínica Electrónica", moscow="MUST HAVE", ok=True,
         nota="Must have: es la base de la que dependen los otros módulos y donde aplica la NTS 139 (HU-001 a HU-004)."),
    dict(nombre="Receta Electrónica / Farmacia", moscow="MUST HAVE", ok=True,
         nota="Must have: la receta elimina el cuaderno de farmacia y los errores de dispensación, con baja complejidad."),
    dict(nombre="Derivaciones (referencias)", moscow="COULD HAVE", ok=False,
         nota="Could have (HU-010): con el CR-002 pasa a la Fase 2. Puede operar manual sin riesgo clínico."),
    dict(nombre="Inventario de medicamentos", moscow="WON'T (ESTA VEZ)", ok=False,
         nota="Won't have en esta fase (HU-009): pasa a la Fase 2. Puede operar manual sin riesgo clínico."),
    dict(nombre="Reportes e indicadores", moscow="FASE 2", ok=False,
         nota="Se difiere a la Fase 2: puede operar manual en el corto plazo sin riesgo clínico."),
]
WSJF = [("HU-003", "Registrar diagnóstico CIE-10", 3.0), ("HU-002", "Registrar triaje", 2.67),
        ("HU-004", "Rectificar registro clínico", 2.67), ("HU-001", "Crear historia clínica", 2.5),
        ("HU-006", "Dispensar receta", 2.33), ("HU-008", "Gestionar usuarios y roles", 2.25),
        ("HU-005", "Emitir receta electrónica", 1.8), ("HU-007", "Consultar auditoría", 1.75)]

# Capítulo 2: conflictos (sección 2.5, Tablas 8, 9 y 10). La alternativa C es la ganadora.
CONFLICTOS_C2 = {
    "c1": dict(
        sala="consultorio", titulo="CONFLICTO 1 · EL MÉDICO VS. EL MINSA", tabla="Tabla 8",
        criterios=[("NTS 139", 40), ("Rapidez ≤ 5 clics", 30), ("Costo", 15), ("Seguridad", 15)],
        alternativas=[
            ("A", "Edición libre sin histórico", (1, 5, 5, 1), 2.80, "Descartada: es rápida, pero infringe la NTS 139."),
            ("B", "Bloqueo total con permiso de jefatura", (5, 1, 3, 5), 3.50, "Descartada: cumple la norma, pero es muy burocrática."),
            ("C", "Inmutabilidad con 'Adenda Ágil'", (5, 5, 4, 5), 4.85, None)],
        acuerdo="Nada se borra: el registro es inmutable. El médico corrige con el botón '+ Nota de Rectificación', "
                "que genera una adenda firmada, y la auditoría corre en segundo plano sin hacer lenta la pantalla.",
        intro=[("jeremy", "Buen día. Estoy atendiendo una consulta y me equivoqué en el diagnóstico.", "neutral"),
               ("carmen", "Soy Carmen, del MINSA. Reviso que las historias clínicas cumplan la NTS 139.", "neutral")],
        antes=[("jeremy", "Si me equivoco en un diagnóstico, necesito corregirlo rápido."),
               ("carmen", "La NTS 139 no permite borrar registros clínicos."),
               ("jeremy", "Pero tengo pacientes esperando. No puedo perder tiempo en cada corrección.", "molesto"),
               ("carmen", "Si borramos algo, ya nadie sabe qué se escribió ni quién lo hizo.", "preocupado"),
               ("yo", "Los dos tienen razón. Evaluemos tres caminos con criterios con peso.")],
        despues=[("jeremy", "Con la nota de rectificación corrijo en segundos."),
                 ("carmen", "Y como nada se borra, la norma se cumple.")]),
    "c2": dict(
        sala="farmacia", titulo="CONFLICTO 2 · FARMACIA VS. PACIENTES", tabla="Tabla 9",
        criterios=[("Menos espera", 35), ("Control de stock", 35), ("Simplicidad", 20), ("Cero papel", 10)],
        alternativas=[
            ("A", "Mantener el cuaderno físico de cargos", (2, 2, 2, 1), 1.90, "Descartada: mantiene los errores del papel."),
            ("B", "Despacho virtual sin validar stock", (5, 1, 4, 5), 3.40, "Descartada: es rápido, pero descuadra el inventario."),
            ("C", "Cola virtual con despacho en 1 clic", (5, 5, 4, 5), 4.80, None)],
        acuerdo="La receta llega al instante a farmacia. El técnico identifica al paciente por DNI, entrega el "
                "medicamento y pulsa 'Dispensar': el stock se descuenta solo (RF-008), sin papel.",
        intro=[("patroclo", "Buenos días. Aquí entregamos los medicamentos y lo anotamos todo en el cuaderno.", "neutral"),
               ("yasuri", "Hola, vengo a recoger mi receta.", "neutral")],
        antes=[("patroclo", "Cada medicamento que sale tiene que descontarse del stock."),
               ("yasuri", "¡Pero no queremos hacer cola para recoger la receta!"),
               ("patroclo", "Y yo no puedo atender rápido si tengo que anotar cada salida a mano.", "molesto"),
               ("yo", "Busquemos la opción que cuide el stock sin hacerlos esperar.")],
        despues=[("patroclo", "Pulso 'Dispensar' y el stock se descuenta solo."),
                 ("yasuri", "Y mi receta llega al instante. ¡Sin colas!")]),
    "c3": dict(
        sala="triaje", titulo="CONFLICTO 3 · LOS QUE REGISTRAN VS. TI", tabla="Tabla 10", apagon=True,
        criterios=[("Seguridad de datos", 35), ("No perder datos", 35), ("Costo", 15), ("Rapidez", 15)],
        alternativas=[
            ("A", "Guardar solo en el servidor", (5, 1, 5, 3), 3.30, "Descartada: si se cae la conexión, se pierden los datos."),
            ("B", "Autoguardado local sin protección", (1, 5, 4, 5), 3.45, "Descartada: deja expuestos los datos de salud."),
            ("C", "Autoguardado local cada 30 s, cifrado", (4, 5, 3, 4), 4.20, None)],
        acuerdo="El sistema guarda en el equipo cada 30 segundos lo que se registra, cifrado, y lo borra cuando "
                "termina de sincronizar con el servidor (RNF-008). No se pierde trabajo y los datos quedan protegidos.",
        intro=[("sara", "Estoy tomando la presión y la temperatura de los pacientes.", "neutral"),
               ("leonidas", "Yo soy de TI. Reviso que los equipos y los datos estén seguros.", "neutral")],
        antes=[("sara", "¡Se cortó la conexión y estaba registrando los signos vitales!"),
               ("leonidas", "Si se guarda en el equipo sin protección, los datos de salud quedan expuestos (Ley 29733)."),
               ("sara", "Si no se guarda en el equipo, pierdo lo que ya registré.", "preocupado"),
               ("leonidas", "Lo entiendo, pero son datos de salud. No pueden quedar expuestos.", "preocupado"),
               ("yo", "Comparemos tres formas de guardar con criterios con peso.")],
        despues=[("sara", "Ahora ya no pierdo lo registrado si se va la conexión."),
                 ("leonidas", "Y los datos viajan cifrados. Así sí.")]),
}
# Expresión del retrato según la situación (assets/retrato_<personaje>_<emocion>.png)
EMO_ANTES = {"jeremy": "preocupado", "carmen": "molesto", "patroclo": "preocupado", "yasuri": "molesto",
             "sara": "angustiado", "leonidas": "molesto", "arian": "preocupado", "yo": "pensativo"}
EMO_DESPUES = {"jeremy": "aliviado", "carmen": "contento", "patroclo": "aliviado", "yasuri": "contento",
               "sara": "aliviado", "leonidas": "contento", "arian": "contento", "yo": "contento"}
# si falta el PNG de una emoción se prueba con una parecida, y al final con la neutral
EMO_PARECIDAS = {"aliviado": ["contento"], "contento": ["aliviado"], "angustiado": ["preocupado"],
                 "preocupado": ["pensativo", "angustiado"], "pensativo": ["preocupado"],
                 "molesto": ["preocupado"], "sorprendido": ["neutral"]}
TAREA_DE_SALA = {"reuniones": "modulos", "consultorio": "c1", "farmacia": "c2", "triaje": "c3"}

# Quién visita qué sala en cada capítulo: id -> (sala, posición en el plano, x en la sala)
VISITAS = {
    2: {"arian": ("reuniones", (28, 212), 140), "carmen": ("consultorio", (296, 68), 150),
        "yasuri": ("farmacia", (528, 270), 200), "leonidas": ("triaje", (200, 262), 160)},
    3: {"yasuri": ("admision", (72, 458), 200)},
}

# Capítulo 3: las 4 puertas del hilo dorado (centro de cada puerta en el plano)
PUERTAS_HILO = [(270, 500), (352, 400), (352, 260), (230, 160)]
INICIO_HILO = (80, 456)                    # donde está María José en el plano

CIERRE = [
    ("Yanela", "Empezamos con un centro de salud de papel y poco presupuesto."),
    ("Mónica", "Elegimos los 2 módulos que más importaban y resolvimos los conflictos con criterios, no a ojo."),
    ("Geradth", "Y cada decisión se puede seguir de punta a punta en el expediente. Estamos listos para sus preguntas."),
]
CREDITOS = "Acori Y. · Candiotti M. · Gaitan G."


# ----------------------------------------------------------------------------
# Juego
# ----------------------------------------------------------------------------
def wrap(font, text, max_w):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if font.size(t)[0] > max_w and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


class Game:
    def __init__(self):
        self.bg = build_background()
        self.world = pygame.Surface((W, H))
        self.chars = pygame.Surface((W, H), pygame.SRCALPHA)   # capa de personajes (va delante del hospital)
        self.bg_ext = build_exterior()
        self.hospital = {}
        for k, path in (("closed", HOSPITAL_CLOSED), ("open", HOSPITAL_OPEN)):
            im = pygame.image.load(res(path)).convert_alpha()
            self.hospital[k] = pygame.transform.scale(im, (im.get_width() * HOSPITAL_SCALE, im.get_height() * HOSPITAL_SCALE))
        hw, hh = self.hospital["closed"].get_size()
        self.hosp_x = (SCREEN_W - hw) // 2
        self.hosp_y = (GROUND + 2) * SCALE - hh
        self.door_cx = (self.hosp_x + DOOR_X_IMG * HOSPITAL_SCALE) / SCALE   # centro de la puerta (píxeles internos)
        self.scene = "ext"        # "ext" = afuera del hospital, "int" = adentro
        self.trans = None         # transición de entrada (puerta, fundido a negro)
        self.door_open = False
        self.fade = 0.0
        self._fade_surf = pygame.Surface((SCREEN_W, SCREEN_H))
        self._fade_surf.fill((0, 0, 0))
        self.player_frames = load_player_frames()
        self.npc_sprites = load_npc_sprites()
        self.px = 24.0
        self.facing = 1           # 1 = derecha
        self.frame = 0
        self.tick = 0
        self.bob = 0.0
        self.correr_toggle = False
        self.collected = []
        self.npc_alpha = {n["id"]: 0.0 for n in NPCS}
        self.c_alpha = {k: 0.0 for k in CONFLICTS}
        self.c_shown = {k: False for k in CONFLICTS}
        self.c_resolved = {k: False for k in CONFLICTS}
        self.banner = ""
        self.banner_t = 0
        self.t = 0
        fam = "segoeui,arial,helvetica,dejavusans,liberationsans"
        self.f_small = pygame.font.SysFont(fam, 16, bold=True)
        self.f_med = pygame.font.SysFont(fam, 19, bold=True)
        self.f_big = pygame.font.SysFont(fam, 24, bold=True)
        self.npc_by_id = {n["id"]: n for n in NPCS}

            # --- hospital nuevo ---
        self.plano = pygame.image.load(res(PLANO_IMG)).convert_alpha()
        self.colis = pygame.image.load(res(PLANO_COL)).convert()
        self.salas = {k: pygame.image.load(res(f"assets/sala_{k}.png")).convert() for k in SALAS}
        self.map_player = load_map_sprites()
        self.npc_front = load_npc_front()
        self.room_of_npc = {s["npc"]: k for k, s in SALAS.items()}
        self.mx, self.my = MAP_START      # posición en el plano
        self.mdir = "espalda"             # hacia dónde mira en el plano
        self.sala = None                  # sala en la que estás (None = no estás en ninguna)
        self.map_back = None              # dónde estabas en el plano antes de entrar a una sala
        self.lock_door = False            # evita que salga el cartel de la puerta justo al volver

    # --- lógica ---
    def zone_at(self, x):
        for z in ZONES:
            if z["x0"] <= x < z["x1"]:
                return z
        return ZONES[-1]

    def show_banner(self, text):
        self.banner, self.banner_t = text, 170

    def near_door(self):
        return abs(self.px + SPRITE / 2 - self.door_cx) < 45

    def press_e(self):
        """Tecla E: entrar al hospital si estás cerca de la puerta."""
        if self.scene == "ext" and self.trans is None and self.near_door():
            self.trans = dict(phase="open", t=0)
            self.door_open = True

    def _update_trans(self):
        tr = self.trans
        tr["t"] += 1
        ph, t = tr["phase"], tr["t"]
        if ph == "open" and t >= 50:             # la puerta ya se abrió
            tr["phase"], tr["t"] = "fadeout", 0
        elif ph == "fadeout":                    # la pantalla se oscurece
            self.fade = min(1.0, t / 70)
            if t >= 70:
                self.scene = "int"               # ahora sí: adentro del hospital
                self.px, self.facing = 40.0, 1
                self.door_open = False
                tr["phase"], tr["t"] = "black", 0
        elif ph == "black":
            self.fade = 1.0
            if t >= 35:
                tr["phase"], tr["t"] = "fadein", 0
                self.show_banner("Adentro del centro de salud: acércate a cada persona")
        elif ph == "fadein":
            self.fade = max(0.0, 1.0 - t / 70)
            if t >= 70:
                self.trans, self.fade = None, 0.0

    def update(self, left, right, up=False, down=False, run=False):
        self.t += 1
        rapido = run or getattr(self, "correr_toggle", False)
        vel = SPEED * (RUN_MULT if rapido else 1.0)
        vx = (vel if right else 0) - (vel if left else 0)
        if self.trans is not None:
            vx = 0
            if self.trans["phase"] in ("open", "fadeout") and self.scene == "ext":
                target = self.door_cx - SPRITE / 2          # el personaje camina hasta la puerta
                if abs(target - self.px) > 1.5:
                    vx = SPEED * 0.8 * (1 if target > self.px else -1)
            self._update_trans()
        max_x = (W if self.scene == "ext" else WORLD_W) - SPRITE
        self.px = max(0, min(max_x, self.px + vx))
        self.bob += 0.20 if rapido else 0.12
        if vx:
            self.facing = 1 if vx > 0 else -1
            self.tick += 1
            ticks = max(3, int(FRAME_TICKS / (RUN_MULT if rapido else 1.0)))
            if self.tick >= ticks:
                self.tick = 0
                self.frame = (self.frame + 1) % len(self.player_frames)
        else:
            self.tick, self.frame = 0, 0
        if self.banner_t > 0:
            self.banner_t -= 1
        if self.scene != "int":
            return                                        # los stakeholders solo existen adentro
        pc = self.px + SPRITE / 2

        for n in NPCS:
            near = abs(pc - n["x"]) < PROX
            self.npc_alpha[n["id"]] += ((1 if near else 0) - self.npc_alpha[n["id"]]) * 0.18
            if near and n["id"] not in self.collected:
                self.collected.append(n["id"])
                self.show_banner(f"{n['name']} — necesidad identificada")
                if len(self.collected) == len(NPCS):
                    self.show_banner("¡Recorrido completo! 8 stakeholders identificados")

        for k, c in CONFLICTS.items():
            a, b = (self.npc_by_id[i] for i in c["members"])
            lo, hi = min(a["x"], b["x"]) - CONFLICT_PAD, max(a["x"], b["x"]) + CONFLICT_PAD
            inside = lo <= pc <= hi
            self.c_alpha[k] += ((1 if inside else 0) - self.c_alpha[k]) * 0.15
            if inside and not self.c_shown[k]:
                self.c_shown[k] = True
                self.show_banner("Conflicto: " + c["label"])
            if pc > hi and not self.c_resolved[k]:
                self.c_resolved[k] = True
                self.show_banner(c["resolution"])

    # --- dibujo ---
    def cam(self):
        if self.scene == "ext":
            return 0
        return int(max(0, min(WORLD_W - W, self.px + SPRITE / 2 - W / 2)))

    def draw_world(self):
        cam = self.cam()
        w = self.world
        if self.scene == "ext":
            w.blit(self.bg_ext, (0, 0))
        else:
            w.blit(self.bg, (0, 0), (cam, 0, W, H))

        # tinte de conflicto
        for k, c in CONFLICTS.items():
            al = self.c_alpha[k] if self.scene == "int" else 0
            if al > 0.02:
                a, b = (self.npc_by_id[i] for i in c["members"])
                lo, hi = min(a["x"], b["x"]) - CONFLICT_PAD - cam, max(a["x"], b["x"]) + CONFLICT_PAD - cam
                tint = pygame.Surface((int(hi - lo), GROUND), pygame.SRCALPHA)
                col = (90, 190, 110) if self.c_resolved[k] else (210, 60, 60)
                tint.fill((*col, int(46 * al * (0.6 if self.c_resolved[k] else 1))))
                w.blit(tint, (lo, 0))

        # personajes (en su propia capa)
        w = self.chars
        w.fill((0, 0, 0, 0))
        pc = self.px + SPRITE / 2
        for n in (NPCS if self.scene == "int" else []):
            img = self.npc_sprites[n["id"]]
            face_right = pc > n["x"]
            if face_right:
                img = pygame.transform.flip(img, True, False)
            bob = int(math.sin(self.t * 0.07 + n["x"]) * 1)
            sx = int(n["x"] - cam - SPRITE / 2)
            sy = GROUND - FEET + bob
            self._shadow(w, sx + SPRITE // 2, GROUND + 1)
            w.blit(img, (sx, sy))

        # jugador (tu dibujo mira a la izquierda, se voltea al ir a la derecha)
        img = self.player_frames[self.frame]
        if self.facing == 1:
            img = pygame.transform.flip(img, True, False)
        sx = int(self.px - cam)
        self._shadow(w, sx + SPRITE // 2, GROUND + 1)
        w.blit(img, (sx, GROUND - FEET))

    @staticmethod
    def _shadow(w, cx, y):
        sw, sh_h = int(22 * CHAR_SCALE), int(6 * CHAR_SCALE)
        sh = pygame.Surface((sw, sh_h), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 60), (0, 0, sw, sh_h))
        w.blit(sh, (cx - sw // 2, y - sh_h // 2))

    def bubble(self, screen, cx, bottom, lines, colors, tail=True, border=(240, 180, 41)):
        pad = 8
        fonts = [self.f_med if i == 0 else self.f_small for i in range(len(lines))]
        ws = [f.size(l)[0] for f, l in zip(fonts, lines)]
        bw = max(ws) + pad * 2
        bh = sum(f.get_linesize() for f in fonts) + pad * 2 - 4
        x = max(8, min(SCREEN_W - bw - 8, cx - bw // 2))
        y = bottom - bh - 10
        pygame.draw.rect(screen, (24, 16, 18), (x, y, bw, bh), border_radius=6)
        pygame.draw.rect(screen, border, (x, y, bw, bh), 2, border_radius=6)
        if tail:
            tx = max(x + 10, min(x + bw - 10, cx))
            pygame.draw.polygon(screen, (24, 16, 18), [(tx - 6, y + bh - 1), (tx + 6, y + bh - 1), (tx, y + bh + 8)])
            pygame.draw.line(screen, border, (tx - 6, y + bh), (tx, y + bh + 8), 2)
            pygame.draw.line(screen, border, (tx + 6, y + bh), (tx, y + bh + 8), 2)
        yy = y + pad - 2
        for f, l, c in zip(fonts, lines, colors):
            screen.blit(f.render(l, True, c), (x + pad, yy))
            yy += f.get_linesize()

    def draw_ui_ext(self, screen):
        """Pantalla de afuera: solo el título, un aviso para entrar y la ayuda de teclas."""
        bar = pygame.Surface((SCREEN_W, 46), pygame.SRCALPHA)
        bar.fill((16, 8, 10, 190))
        screen.blit(bar, (0, 0))
        screen.blit(self.f_small.render("DIRESA LA LIBERTAD · IDENTIFICACIÓN DE STAKEHOLDERS", True, (251, 234, 208)), (16, 14))
        zi = self.f_med.render("Exterior · Centro de salud", True, (240, 180, 41))
        screen.blit(zi, (SCREEN_W - zi.get_width() - 16, 12))
        if self.trans is None and self.near_door():
            t = self.f_big.render("Presione E para entrar", True, (251, 234, 208))
            bw, bh = t.get_width() + 36, t.get_height() + 18
            x, y = (SCREEN_W - bw) // 2, SCREEN_H - 78
            pygame.draw.rect(screen, (24, 16, 18), (x, y, bw, bh), border_radius=8)
            pygame.draw.rect(screen, (240, 180, 41), (x, y, bw, bh), 2, border_radius=8)
            screen.blit(t, (x + 18, y + 9))
        screen.blit(self.f_small.render("Flechas  < >  o  A / D  para moverte", True, (255, 248, 236)), (16, SCREEN_H - 28))

    def draw_ui(self, screen):
        if self.scene == "ext":
            self.draw_ui_ext(screen)
            return
        cam = self.cam()
        pc = self.px + SPRITE / 2

        # etiquetas / globos de los personajes
        for n in NPCS:
            sx = (n["x"] - cam) * SCALE
            top = (GROUND - FEET) * SCALE
            conflict = n.get("conflict")
            if conflict and not self.c_resolved[conflict] and self.c_alpha[conflict] > 0.5:
                # los dos personajes "discuten": cada uno con su globo
                self.bubble(screen, sx, top, [n["says"], n["name"]],
                            [(255, 225, 205), (240, 180, 41)], border=(220, 90, 90))
            elif self.npc_alpha[n["id"]] > 0.5:
                nm = wrap(self.f_med, n["name"], 260)
                self.bubble(screen, sx, top, nm + [n["role"]],
                            [(251, 234, 208)] * len(nm) + [(240, 180, 41)])
            elif n["id"] in self.collected:
                # marca de "identificado": check verde sobre la cabeza
                cx, cy = int(sx), int(top - 10)
                pygame.draw.lines(screen, (95, 190, 110), False, [(cx - 8, cy), (cx - 2, cy + 7), (cx + 9, cy - 8)], 4)
            # rayo de conflicto entre los dos
        for k, c in CONFLICTS.items():
            if self.c_alpha[k] > 0.3 and not self.c_resolved[k]:
                a, b = (self.npc_by_id[i] for i in c["members"])
                mx = ((a["x"] + b["x"]) / 2 - cam) * SCALE
                my = 42 * SCALE + math.sin(self.t * 0.2) * 4
                pygame.draw.polygon(screen, (255, 210, 60), [(mx + 6, my - 28), (mx - 12, my + 4), (mx - 1, my + 4),
                                                              (mx - 8, my + 28), (mx + 14, my - 6), (mx + 2, my - 6)])
                pygame.draw.polygon(screen, (160, 60, 30), [(mx + 6, my - 28), (mx - 12, my + 4), (mx - 1, my + 4),
                                                             (mx - 8, my + 28), (mx + 14, my - 6), (mx + 2, my - 6)], 2)

        # barra superior
        bar = pygame.Surface((SCREEN_W, 46), pygame.SRCALPHA)
        bar.fill((16, 8, 10, 190))
        screen.blit(bar, (0, 0))
        screen.blit(self.f_small.render("DIRESA LA LIBERTAD · IDENTIFICACIÓN DE STAKEHOLDERS", True, (251, 234, 208)), (16, 14))
        track = pygame.Rect(600, 17, 320, 12)
        pygame.draw.rect(screen, (70, 62, 62), track, border_radius=6)
        frac = self.px / (WORLD_W - SPRITE)
        pygame.draw.rect(screen, (240, 180, 41), (track.x, track.y, int(track.w * frac), track.h), border_radius=6)
        pygame.draw.rect(screen, (150, 140, 140), track, 1, border_radius=6)
        z = self.zone_at(pc)["name"]
        zi = self.f_med.render(z, True, (240, 180, 41))
        screen.blit(zi, (SCREEN_W - zi.get_width() - 16, 12))

        # panel de requisitos
        pw, ph = 330, 60 + 24 * max(1, len(self.collected))
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(panel, (20, 12, 10, 190), (0, 0, pw, ph), border_radius=10)
        pygame.draw.rect(panel, (255, 255, 255, 50), (0, 0, pw, ph), 1, border_radius=10)
        screen.blit(panel, (SCREEN_W - pw - 14, 56))
        screen.blit(self.f_small.render("REQUISITOS IDENTIFICADOS", True, (240, 180, 41)), (SCREEN_W - pw, 66))
        if not self.collected:
            screen.blit(self.f_small.render("Avanza y acércate a cada persona…", True, (170, 160, 150)), (SCREEN_W - pw, 92))
        for i, nid in enumerate(self.collected):
            n = self.npc_by_id[nid]
            y = 92 + i * 24
            pygame.draw.rect(screen, (240, 180, 41), (SCREEN_W - pw, y + 1, 3, 17))
            txt = f"{n['name'].split(' / ')[0]}: {n['need']}"
            while self.f_small.size(txt)[0] > pw - 24 and len(txt) > 8:
                txt = txt[:-2]
            if txt != f"{n['name'].split(' / ')[0]}: {n['need']}":
                txt = txt.rstrip() + "…"
            screen.blit(self.f_small.render(txt, True, (255, 248, 236)), (SCREEN_W - pw + 10, y))

        # aviso central
        if self.banner_t > 0:
            al = min(1.0, self.banner_t / 30)
            t = self.f_big.render(self.banner, True, (251, 234, 208))
            bw, bh = t.get_width() + 32, t.get_height() + 16
            b = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(b, (20, 12, 10, int(220 * al)), (0, 0, bw, bh), border_radius=8)
            pygame.draw.rect(b, (240, 180, 41, int(255 * al)), (0, 0, bw, bh), 2, border_radius=8)
            t.set_alpha(int(255 * al))
            b.blit(t, (16, 8))
            screen.blit(b, ((SCREEN_W - bw) // 2 - 80, 60))

        screen.blit(self.f_small.render("Flechas  < >  o  A / D  para moverte", True, (255, 248, 236)), (16, SCREEN_H - 28))

    def render(self, screen):
        self.draw_world()
        pygame.transform.scale(self.world, (SCREEN_W, SCREEN_H), screen)
        if self.scene == "ext":
            screen.blit(self.hospital["open" if self.door_open else "closed"], (self.hosp_x, self.hosp_y))
        screen.blit(pygame.transform.scale(self.chars, (SCREEN_W, SCREEN_H)), (0, 0))
        self.draw_ui(screen)
        if self.fade > 0:                                   # fundido a negro
            self._fade_surf.set_alpha(int(255 * self.fade))
            screen.blit(self._fade_surf, (0, 0))

    # ======================================================================
    # HOSPITAL NUEVO (pega todo esto al final de la clase Game)
    # ======================================================================
    def _update_trans(self):
        """Transiciones con oscurecimiento: entrar al hospital, entrar a una sala y volver al plano."""
        tr = self.trans
        tr["t"] += 1
        ph, t = tr["phase"], tr["t"]
        kind = tr.get("kind", "hospital")
        t_out, t_black, t_in = (70, 35, 70) if kind == "hospital" else (25, 10, 25)
        if ph == "open" and t >= 50:             # la puerta ya se abrió
            tr["phase"], tr["t"] = "fadeout", 0
        elif ph == "fadeout":                    # la pantalla se oscurece
            self.fade = min(1.0, t / t_out)
            if t >= t_out:
                self._cambiar_escena(tr)
                tr["phase"], tr["t"] = "black", 0
        elif ph == "black":
            self.fade = 1.0
            if t >= t_black:
                tr["phase"], tr["t"] = "fadein", 0
                if kind == "hospital":
                    self.show_banner("Recorre los pasillos y entra a cada sala")
        elif ph == "fadein":
            self.fade = max(0.0, 1.0 - t / t_in)
            if t >= t_in:
                self.trans, self.fade = None, 0.0

    def _cambiar_escena(self, tr):
        """Se llama cuando la pantalla ya está negra: aquí cambia el escenario."""
        kind = tr.get("kind", "hospital")
        if kind == "hospital":                   # de la calle al plano del hospital
            self.scene = "map"
            self.mx, self.my = MAP_START
            self.mdir = "espalda"
            self.door_open = False
        elif kind == "sala":                     # del plano a una sala (vista de perfil)
            self.map_back = (self.mx, self.my, self.mdir)
            self.sala = tr["sala"]
            self.scene = "sala"
            self.px, self.facing = 70.0, 1
        elif kind == "mapa":                     # de la sala de vuelta al plano
            self.scene = "map"
            self.mx, self.my, self.mdir = self.map_back
            self.sala = None
            self.lock_door = True

    def update(self, left, right, up=False, down=False, run=False):
        self.t += 1
        if self.banner_t > 0:
            self.banner_t -= 1
        bloqueado = self.trans is not None
        if bloqueado:
            self._update_trans()
        rapido = run or getattr(self, "correr_toggle", False)
        if self.scene == "map":
            self.update_mapa(left, right, up, down, bloqueado, rapido=rapido)
        else:
            self.update_lado(left, right, bloqueado, rapido=rapido)

    def _animar(self, moviendose, rapido=False):
        if moviendose:
            self.tick += 1
            ticks = max(3, int(FRAME_TICKS / (RUN_MULT if rapido else 1.0)))
            if self.tick >= ticks:
                self.tick = 0
                self.frame = (self.frame + 1) % 4
        else:
            self.tick, self.frame = 0, 0

    def update_lado(self, left, right, bloqueado, rapido=False):
        """Movimiento de lado: la calle (ext) y las salas."""
        vel = SPEED * (RUN_MULT if rapido else 1.0)
        vx = (vel if right else 0) - (vel if left else 0)
        if bloqueado:
            vx = 0
            tr = self.trans
            if tr is not None and tr.get("kind", "hospital") == "hospital" and tr["phase"] in ("open", "fadeout") and self.scene == "ext":
                target = self.door_cx - SPRITE / 2          # el personaje camina hasta la puerta
                if abs(target - self.px) > 1.5:
                    vx = SPEED * 0.8 * (1 if target > self.px else -1)
        self.px = max(0, min(W - SPRITE, self.px + vx))
        if vx:
            self.facing = 1 if vx > 0 else -1
        self._animar(vx != 0, rapido)
        self.bob += 0.20 if rapido else 0.12
        if self.scene == "sala" and not bloqueado:
            self._update_sala()

    def _libre(self, x, y):
        """True si los pies del personaje (en x, y) pisan una zona caminable del plano."""
        for fx, fy in ((x + 10, y + 26), (x + 21, y + 26), (x + 10, y + 30), (x + 21, y + 30)):
            if not (0 <= fx < self.colis.get_width() and 0 <= fy < self.colis.get_height()):
                return False
            if tuple(self.colis.get_at((int(fx), int(fy))))[:3] == (0, 0, 0):
                return False
        return True

    def _puerta_actual(self):
        """Nombre de la sala si estás parado en una zona de puerta; si no, None."""
        c = tuple(self.colis.get_at((int(self.mx + 16), int(self.my + 28))))[:3]
        return DOOR_COLORS.get(c)

    def map_pos(self, npc_id):
        return SALAS[self.room_of_npc[npc_id]]["map_pos"]

    def cam_mapa(self):
        cx = int(max(0, min(self.plano.get_width() - W, self.mx + 16 - W / 2)))
        cy = int(max(0, min(self.plano.get_height() - H, self.my + 16 - 120)))
        return cx, cy

    def update_mapa(self, left, right, up, down, bloqueado, rapido=False):
        dx = (1 if right else 0) - (1 if left else 0)
        dy = (1 if down else 0) - (1 if up else 0)
        if bloqueado:
            dx = dy = 0
        k = 0.707 if (dx and dy) else 1.0               # en diagonal no corre más rápido
        vel = MAP_SPEED * (RUN_MULT if rapido else 1.0)
        vx, vy = dx * vel * k, dy * vel * k
        movio = False
        pasos = max(1, int(math.ceil(max(abs(vx), abs(vy)))))
        svx, svy = vx / pasos, vy / pasos
        for _ in range(pasos):
            if svx and self._libre(self.mx + svx, self.my):   # se mueve por separado en X y en Y
                self.mx += svx
                movio = True
            if svy and self._libre(self.mx, self.my + svy):
                self.my += svy
                movio = True
        if dy:                                          # W = espalda, S = frente, A = izquierda, D = derecha
            self.mdir = "frente" if dy > 0 else "espalda"
        elif dx:
            self.mdir = "derecha" if dx > 0 else "izquierda"
        self._animar(movio, rapido)

        pcx, pcy = self.mx + 16, self.my + 22
        for n in NPCS:                                  # nombre sobre el stakeholder cuando pasas cerca
            nx, ny = self.map_pos(n["id"])
            near = math.hypot(pcx - (nx + 16), pcy - (ny + 22)) < 60
            self.npc_alpha[n["id"]] += ((1 if near else 0) - self.npc_alpha[n["id"]]) * 0.18
        for key, c in CONFLICTS.items():                # discusión entre dos stakeholders
            ax, ay = self.map_pos(c["members"][0])
            bx, by = self.map_pos(c["members"][1])
            d = math.hypot(self.mx - (ax + bx) / 2, self.my - (ay + by) / 2)
            cerca = d < CONFLICT_RADIUS and not self.c_resolved[key]
            self.c_alpha[key] += ((1 if cerca else 0) - self.c_alpha[key]) * 0.15
            if cerca and not self.c_shown[key]:
                self.c_shown[key] = True
                self.show_banner("Conflicto: " + c["label"])
        if self._puerta_actual() is None:
            self.lock_door = False

    def _update_sala(self):
        info = SALAS[self.sala]
        n = self.npc_by_id[info["npc"]]
        near = abs((self.px + SPRITE / 2) - (info["x"] + SPRITE / 2)) < PROX
        self.npc_alpha[n["id"]] += ((1 if near else 0) - self.npc_alpha[n["id"]]) * 0.18
        if near and n["id"] not in self.collected:
            self._recoger(n)

    def _recoger(self, n):
        self.collected.append(n["id"])
        self.show_banner(f"{n['name']} — necesidad identificada")
        for key, c in CONFLICTS.items():                # si ya conoces a los dos, el conflicto se resuelve
            if not self.c_resolved[key] and all(i in self.collected for i in c["members"]):
                self.c_resolved[key] = True
                self.show_banner(c["resolution"])
        if len(self.collected) == len(NPCS):
            self.show_banner("¡Recorrido completo! 8 stakeholders identificados")

    # --- dibujo ---
    def _dibujar_jugador_lado(self, w):
        img = self.player_frames[self.frame]            # tu dibujo mira a la izquierda; se voltea al ir a la derecha
        if self.facing == 1:
            img = pygame.transform.flip(img, True, False)
        sx = int(self.px)
        self._shadow(w, sx + SPRITE // 2, GROUND + 1)
        w.blit(img, (sx, GROUND - FEET))

    def draw_world(self):
        w = self.world
        cw = self.chars
        cw.fill((0, 0, 0, 0))
        if self.scene == "ext":
            w.blit(self.bg_ext, (0, 0))
            self._dibujar_jugador_lado(cw)
        elif self.scene == "map":
            cx, cy = self.cam_mapa()
            w.blit(self.plano, (0, 0), (cx, cy, W, H))
            lista = []                                  # se dibuja de arriba hacia abajo para que se tapen bien
            for n in NPCS:
                nx, ny = self.map_pos(n["id"])
                lista.append((ny, self.npc_front[n["id"]], nx - cx, ny - cy))
            lista.append((self.my, self.map_player[self.mdir][self.frame], self.mx - cx, self.my - cy))
            for _, im, x, y in sorted(lista, key=lambda t: t[0]):
                cw.blit(im, (int(x), int(y)))
        else:                                           # sala de perfil
            w.blit(self.salas[self.sala], (0, 0))
            info = SALAS[self.sala]
            img = self.npc_sprites[info["npc"]]
            if self.px + SPRITE / 2 > info["x"] + SPRITE / 2:
                img = pygame.transform.flip(img, True, False)
            bob = int(math.sin(self.t * 0.07 + info["x"]) * 1)
            self._shadow(cw, info["x"] + SPRITE // 2, GROUND + 1)
            cw.blit(img, (info["x"], GROUND - FEET + bob))
            self._dibujar_jugador_lado(cw)

    def bubble(self, screen, cx, bottom, lines, colors, tail=True, border=(240, 180, 41), feet=None):
        pad = 8
        fonts = [self.f_med if i == 0 else self.f_small for i in range(len(lines))]
        ws = [f.size(l)[0] for f, l in zip(fonts, lines)]
        bw = max(ws) + pad * 2
        bh = sum(f.get_linesize() for f in fonts) + pad * 2 - 4
        x = max(8, min(SCREEN_W - bw - 8, cx - bw // 2))
        y = bottom - bh - 10
        arriba = True
        if feet is not None and y < 52:                 # si no cabe arriba, el globo va debajo del personaje
            y, arriba = feet + 12, False
        pygame.draw.rect(screen, (24, 16, 18), (x, y, bw, bh), border_radius=6)
        pygame.draw.rect(screen, border, (x, y, bw, bh), 2, border_radius=6)
        if tail:
            tx = max(x + 10, min(x + bw - 10, cx))
            if arriba:
                pygame.draw.polygon(screen, (24, 16, 18), [(tx - 6, y + bh - 1), (tx + 6, y + bh - 1), (tx, y + bh + 8)])
                pygame.draw.line(screen, border, (tx - 6, y + bh), (tx, y + bh + 8), 2)
                pygame.draw.line(screen, border, (tx + 6, y + bh), (tx, y + bh + 8), 2)
            else:
                pygame.draw.polygon(screen, (24, 16, 18), [(tx - 6, y + 1), (tx + 6, y + 1), (tx, y - 8)])
                pygame.draw.line(screen, border, (tx - 6, y), (tx, y - 8), 2)
                pygame.draw.line(screen, border, (tx + 6, y), (tx, y - 8), 2)
        yy = y + pad - 2
        for f, l, c in zip(fonts, lines, colors):
            screen.blit(f.render(l, True, c), (x + pad, yy))
            yy += f.get_linesize()

    def _aviso_e(self, screen, texto):
        t = self.f_big.render(texto, True, (251, 234, 208))
        bw, bh = t.get_width() + 36, t.get_height() + 18
        x, y = (SCREEN_W - bw) // 2, SCREEN_H - 78
        pygame.draw.rect(screen, (24, 16, 18), (x, y, bw, bh), border_radius=8)
        pygame.draw.rect(screen, (240, 180, 41), (x, y, bw, bh), 2, border_radius=8)
        screen.blit(t, (x + 18, y + 9))

    def _globo_stakeholder(self, screen, n, sx, top, feet, en_mapa):
        conflict = n.get("conflict")
        if conflict and not self.c_resolved[conflict] and (self.c_alpha[conflict] > 0.5 if en_mapa else self.npc_alpha[n["id"]] > 0.5):
            # los dos stakeholders "discuten": cada uno con su globo
            self.bubble(screen, sx, top, [n["says"], n["name"]], [(255, 225, 205), (240, 180, 41)],
                        border=(220, 90, 90), feet=feet)
        elif self.npc_alpha[n["id"]] > 0.5:
            nm = wrap(self.f_med, n["name"], 260)
            self.bubble(screen, sx, top, nm + [n["role"]], [(251, 234, 208)] * len(nm) + [(240, 180, 41)], feet=feet)
        elif n["id"] in self.collected:
            cx, cy = int(sx), int(top - 10)             # marca de "identificado": check verde sobre la cabeza
            pygame.draw.lines(screen, (95, 190, 110), False, [(cx - 8, cy), (cx - 2, cy + 7), (cx + 9, cy - 8)], 4)

    def draw_ui(self, screen):
        if self.scene == "ext":
            self.draw_ui_ext(screen)
            return
        if self.scene == "map":
            cx, cy = self.cam_mapa()
            for n in NPCS:
                nx, ny = self.map_pos(n["id"])
                sx = (nx + 16 - cx) * SCALE
                top = (ny - cy) * SCALE
                feet = (ny + 30 - cy) * SCALE
                if 0 <= sx <= SCREEN_W and 0 <= feet <= SCREEN_H:
                    self._globo_stakeholder(screen, n, sx, top, feet, True)
            zona = "Centro de salud"
            ayuda = "Flechas  o  W A S D  para moverte"
        else:
            info = SALAS[self.sala]
            n = self.npc_by_id[info["npc"]]
            self._globo_stakeholder(screen, n, (info["x"] + SPRITE / 2) * SCALE, (GROUND - FEET) * SCALE, None, False)
            zona = info["name"]
            ayuda = "Flechas  < >  o  A / D  para moverte"

        # barra superior con el progreso
        bar = pygame.Surface((SCREEN_W, 46), pygame.SRCALPHA)
        bar.fill((16, 8, 10, 190))
        screen.blit(bar, (0, 0))
        screen.blit(self.f_small.render("DIRESA LA LIBERTAD · IDENTIFICACIÓN DE STAKEHOLDERS", True, (251, 234, 208)), (16, 14))
        track = pygame.Rect(600, 17, 320, 12)
        pygame.draw.rect(screen, (70, 62, 62), track, border_radius=6)
        frac = len(self.collected) / len(NPCS)
        pygame.draw.rect(screen, (240, 180, 41), (track.x, track.y, int(track.w * frac), track.h), border_radius=6)
        pygame.draw.rect(screen, (150, 140, 140), track, 1, border_radius=6)
        zi = self.f_med.render(zona, True, (240, 180, 41))
        screen.blit(zi, (SCREEN_W - zi.get_width() - 16, 12))

        # panel de requisitos
        pw, ph = 330, 60 + 24 * max(1, len(self.collected))
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(panel, (20, 12, 10, 190), (0, 0, pw, ph), border_radius=10)
        pygame.draw.rect(panel, (255, 255, 255, 50), (0, 0, pw, ph), 1, border_radius=10)
        screen.blit(panel, (SCREEN_W - pw - 14, 56))
        screen.blit(self.f_small.render("REQUISITOS IDENTIFICADOS", True, (240, 180, 41)), (SCREEN_W - pw, 66))
        if not self.collected:
            screen.blit(self.f_small.render("Entra a cada sala y acércate a la persona…", True, (170, 160, 150)), (SCREEN_W - pw, 92))
        for i, nid in enumerate(self.collected):
            n = self.npc_by_id[nid]
            y = 92 + i * 24
            pygame.draw.rect(screen, (240, 180, 41), (SCREEN_W - pw, y + 1, 3, 17))
            txt = f"{n['name'].split(' / ')[0]}: {n['need']}"
            while self.f_small.size(txt)[0] > pw - 24 and len(txt) > 8:
                txt = txt[:-2]
            if txt != f"{n['name'].split(' / ')[0]}: {n['need']}":
                txt = txt.rstrip() + "…"
            screen.blit(self.f_small.render(txt, True, (255, 248, 236)), (SCREEN_W - pw + 10, y))

        # aviso central
        if self.banner_t > 0:
            al = min(1.0, self.banner_t / 30)
            t = self.f_big.render(self.banner, True, (251, 234, 208))
            bw, bh = t.get_width() + 32, t.get_height() + 16
            b = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(b, (20, 12, 10, int(220 * al)), (0, 0, bw, bh), border_radius=8)
            pygame.draw.rect(b, (240, 180, 41, int(255 * al)), (0, 0, bw, bh), 2, border_radius=8)
            t.set_alpha(int(255 * al))
            b.blit(t, (16, 8))
            screen.blit(b, ((SCREEN_W - bw) // 2 - 80, 60))

        # cartel "Presione E"
        if self.trans is None:
            if self.scene == "map" and not self.lock_door and self._puerta_actual():
                self._aviso_e(screen, "Presione E para entrar")
            elif self.scene == "sala" and self.px < 34:
                self._aviso_e(screen, "Presione E para salir")
        screen.blit(self.f_small.render(ayuda, True, (255, 248, 236)), (16, SCREEN_H - 28))

    def press_e(self):
        """Tecla E: entrar al hospital, entrar a una sala o salir de ella."""
        if self.trans is not None:
            return
        if self.scene == "ext" and self.near_door():
            self.trans = dict(kind="hospital", phase="open", t=0)
            self.door_open = True
        elif self.scene == "map" and not self.lock_door:
            sala = self._puerta_actual()
            if sala:
                self.trans = dict(kind="sala", phase="fadeout", t=0, sala=sala)
        elif self.scene == "sala" and self.px < 34:
            self.trans = dict(kind="mapa", phase="fadeout", t=0)

    # ======================================================================
    # INTERFAZ PIXEL ART + CAPÍTULO 1 (pega todo esto al final de la clase Game)
    # ======================================================================
    menu = None              # menú del buzón: None = cerrado, si no {"sel": capítulo elegido}

    def _ui_init(self):
        """Prepara la interfaz, las caritas y el estado de los capítulos. Se llama sola la primera vez."""
        if hasattr(self, "ui"):
            return
        self.ui = pygame.Surface((W, H), pygame.SRCALPHA)       # capa de la interfaz (384x216)
        self.panel_visible = True                               # TAB muestra / oculta el panel
        self.caras, self.siluetas = {}, {}
        for n in NPCS:
            cara = self.npc_front[n["id"]].subsurface((8, 1, 16, 14)).copy()   # solo la cabeza
            self.caras[n["id"]] = cara
            self.siluetas[n["id"]] = pygame.mask.from_surface(cara).to_surface(
                setcolor=(44, 58, 94, 255), unsetcolor=(0, 0, 0, 0))
        self._fase = {n["id"]: i * 53 for i, n in enumerate(NPCS)}   # para que no se muevan todos igual
        self._sombra_mapa = pygame.Surface((14, 4), pygame.SRCALPHA)
        pygame.draw.ellipse(self._sombra_mapa, (0, 0, 0, 60), (0, 0, 14, 4))
        # --- capítulos ---
        self.capitulo = 1                 # capítulo que estás jugando
        self.desbloqueados = 1            # cuántos capítulos se pueden elegir en el buzón
        self.logros = []                  # logros ya obtenidos
        self.logro_txt, self.logro_t = "", 0
        self.buzon_nuevo = False          # True = el buzón tiene algo nuevo (banderita arriba)
        self._apagar_conflictos()

    def _apagar_conflictos(self):
        """En el Capítulo 1 no hay conflictos: se marcan como 'ya vistos' para que no aparezcan."""
        for k in CONFLICTS:
            self.c_resolved[k] = True
            self.c_shown[k] = True
            self.c_alpha[k] = 0.0

    # --- capítulos, buzón, logro y salida ------------------------------------
    def _recoger(self, n):
        """Conoces a un stakeholder. Al conocer a los 8 se gana el logro del Capítulo 1."""
        self.collected.append(n["id"])
        self.show_banner(f"{n['name']}: stakeholder identificado")
        if len(self.collected) == len(NPCS) and self.capitulo == 1:
            self._logro(CAPITULOS[0]["logro"])
            self.desbloqueados = max(self.desbloqueados, 2)
            self.buzon_nuevo = True
            self.show_banner("¡Misión cumplida! Sal del centro de salud y revisa el buzón")

    def _logro(self, texto):
        if texto and texto not in self.logros:              # cada logro sale una sola vez
            self.logros.append(texto)
            self.logro_txt, self.logro_t = texto, 300

    def cerca_buzon(self):
        return self.scene == "ext" and abs(self.px + SPRITE / 2 - BUZON_X) < 22

    def en_salida(self):
        """True si en el plano estás parado en la puerta de entrada (para salir a la calle)."""
        x1, y1, x2, y2 = SALIDA_MAPA
        fx, fy = self.mx + 16, self.my + 30
        return self.scene == "map" and x1 <= fx <= x2 and y1 <= fy <= y2

    def tecla(self, key):
        """Todas las teclas que se presionan una vez. Devuelve 'salir' para cerrar el juego."""
        self._ui_init()
        if self.menu is not None:                           # con el menú del buzón abierto
            libres = self.desbloqueados
            if key in (pygame.K_UP, pygame.K_w):
                self.menu["sel"] = (self.menu["sel"] - 1) % libres
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.menu["sel"] = (self.menu["sel"] + 1) % libres
            elif key in (pygame.K_e, pygame.K_RETURN, pygame.K_SPACE):
                self._elegir_capitulo()
            elif key == pygame.K_ESCAPE:
                self.menu = None
            return None
        if key == pygame.K_ESCAPE:
            return "salir"
        if key == pygame.K_c:
            self.correr_toggle = not getattr(self, "correr_toggle", False)
            self.show_banner("Modo rápido: " + ("ACTIVADO" if self.correr_toggle else "DESACTIVADO"))
        elif key == pygame.K_TAB:
            self.panel_visible = not self.panel_visible
        elif key == pygame.K_e and self.trans is None:
            if self.cerca_buzon():
                self._abrir_buzon()
            elif self.en_salida():
                self.trans = dict(kind="calle", phase="fadeout", t=0)
            else:
                self.press_e()
        return None

    def _abrir_buzon(self):
        if self.desbloqueados < 2:                          # al inicio el buzón no deja hacer nada
            self.show_banner("El buzón está vacío: termina primero el Capítulo 1")
            return
        self.menu = dict(sel=min(self.capitulo, self.desbloqueados) - 1)
        self.buzon_nuevo = False

    def _elegir_capitulo(self):
        sel = self.menu["sel"]
        self.menu = None
        if sel == 0:                                        # Capítulo 1: se vuelve a jugar desde cero
            self.capitulo = 1
            self.collected = []
            for k in self.npc_alpha:
                self.npc_alpha[k] = 0.0
            self._apagar_conflictos()
            self.show_banner("Capítulo 1: " + CAPITULOS[0]["titulo"])
        else:                                               # los demás capítulos aún no están hechos
            self.show_banner(f"Capítulo {sel + 1}: ¡Próximamente!")

    def _cambiar_escena(self, tr):
        """Se llama cuando la pantalla ya está negra: aquí cambia el escenario."""
        kind = tr.get("kind", "hospital")
        if kind == "hospital":                   # de la calle al plano del hospital
            self.scene = "map"
            self.mx, self.my = MAP_START
            self.mdir = "espalda"
            self.door_open = False
        elif kind == "sala":                     # del plano a una sala (vista de perfil)
            self.map_back = (self.mx, self.my, self.mdir)
            self.sala = tr["sala"]
            self.scene = "sala"
            self.px, self.facing = 70.0, 1
        elif kind == "mapa":                     # de la sala de vuelta al plano
            self.scene = "map"
            self.mx, self.my, self.mdir = self.map_back
            self.sala = None
            self.lock_door = True
        elif kind == "calle":                    # del plano de vuelta a la calle (frente a la puerta)
            self.scene = "ext"
            self.px, self.facing = self.door_cx - SPRITE / 2, -1
            self.door_open = False
            self.frame = 0

    # --- los stakeholders hacen algo -----------------------------------------
    def _actividad(self, n):
        """Lo que hace cada uno. Yasuri de visita (farmacia, admisión) espera tranquila en vez de bailar."""
        if n["id"] == "yasuri" and getattr(self, "capitulo", 1) > 1:
            return "espera"
        return n.get("actividad", "")

    def _pose(self, n):
        """Movimiento según la actividad: (dx, dy, voltear). En píxeles del plano.
        voltear = None significa 'que mire hacia ti' (en las salas)."""
        t = self.t + self._fase.get(n["id"], 0)
        act = self._actividad(n)
        if act == "baila":                                  # salta al ritmo y cambia de lado
            return int(math.sin(t * 0.105) * 2), -int(abs(math.sin(t * 0.21)) * 3), (t // 30) % 2 == 1
        if act == "pasea":                                  # camina de un lado a otro
            p = (t % 240) / 240
            tri = p * 2 if p < 0.5 else 2 - p * 2
            return int((tri - 0.5) * 20), -((t // 8) % 2), p < 0.5
        if act == "teclea":                                 # tiembla un poquito, como tecleando
            return 0, -((t // 5) % 2), None
        if act == "signos":                                 # mira al paciente y luego al monitor
            return 0, -int(abs(math.sin(t * 0.05)) * 1.5), (t // 120) % 2 == 1
        if act == "inspecciona":                            # mira a un lado y al otro
            mira = (t // 50) % 2 == 1
            return (2 if mira else -2), 0, mira
        if act == "acomoda":                                # va de lado a lado acomodando cajitas
            return int(math.sin(t * 0.04) * 4), (-1 if t % 60 < 8 else 0), math.cos(t * 0.04) > 0
        if act == "telefono":                               # habla por teléfono
            return 0, -int(abs(math.sin(t * 0.06)) * 1.5), None
        if act == "archiva":                                # sella historias clínicas: ¡pum!
            p = t % 48
            return 0, (-2 if p < 6 else (1 if p < 9 else 0)), (t // 96) % 2 == 1
        return 0, int(math.sin(t * 0.07)), None

    def _particulas(self, s, n, cx, top, esc):
        """Partículas alrededor de cada stakeholder. cx = centro, top = arriba del dibujo, esc = 1 plano / 2 sala."""
        t = self.t + self._fase.get(n["id"], 0)
        act = self._actividad(n)
        if act == "baila":                                  # notas musicales de colores
            colores = ((255, 214, 64), (120, 220, 255), (255, 130, 200))
            for k in range(3):
                p = (t + k * 22) % 66
                x = cx + (k - 1) * 10 * esc + math.sin(p * 0.15 + k) * 3 * esc
                px_icono(s, x - 2 * esc, top + 6 * esc - p * 0.45 * esc, P_NOTA, colores[k], esc)
        elif act == "signos":                               # corazoncitos (signos vitales)
            p = t % 50
            if p < 40:
                px_icono(s, cx + 8 * esc, top + 4 * esc - p * 0.35 * esc, P_CORAZON, (230, 60, 80), esc)
        elif act == "pasea":                                # gotitas de sudor (anda apurado)
            p = t % 70
            if p < 30:
                px_icono(s, cx + 7 * esc, top + 3 * esc + p * 0.2 * esc, P_GOTA, (120, 200, 255), esc)
        elif act == "teclea":                               # ceros y unos
            for k in range(2):
                p = (t + k * 25) % 50
                g = P_UNO if ((t + k * 25) // 50 + k) % 2 else P_CERO
                px_icono(s, cx + (-9 + k * 15) * esc, top + 6 * esc - p * 0.4 * esc, g, (110, 230, 130), esc)
        elif act == "inspecciona":                          # checks verdes (revisa que todo cumpla)
            p = t % 60
            if p < 45:
                px_icono(s, cx + 9 * esc, top + 2 * esc - p * 0.3 * esc, P_CHECK, (110, 220, 120), esc)
        elif act == "acomoda":                              # pastillitas que salta y atrapa
            for k in range(2):
                p = (t + k * 30) % 60
                x = cx + (-7 + k * 10) * esc + (p * 0.12 if k else -p * 0.12) * esc
                y = top + 16 * esc - (p * 1.1 - p * p * 0.02) * esc
                px_icono(s, x, y, P_PASTILLA, (250, 250, 250), esc, (230, 80, 80) if k else (90, 150, 240))
        elif act == "archiva":                              # hojas que vuelan y el sello que baja
            for k in range(2):
                p = (t + k * 24) % 48
                x = cx + (-10 + k * 16) * esc + math.sin(p * 0.2 + k) * 2 * esc
                px_icono(s, x, top + 8 * esc - p * 0.4 * esc, P_HOJA, (250, 250, 246), esc, (150, 156, 176))
            if t % 48 < 9:
                px_icono(s, cx + 8 * esc, top - 2 * esc, P_SELLO, (200, 60, 70), esc, (120, 30, 40))
        elif act == "telefono":                             # globito con puntos: "..."
            puntos = (t // 18) % 4
            bx, by = int(cx + 8 * esc), int(top - 3 * esc)
            ui_rect(s, UI_LINEA, bx, by, 13 * esc, 7 * esc)
            ui_rect(s, (250, 250, 250), bx + esc, by + esc, 11 * esc, 5 * esc)
            ui_rect(s, UI_LINEA, bx + esc, by + 7 * esc, 2 * esc, esc)
            for k in range(puntos):
                ui_rect(s, UI_LINEA, bx + (3 + k * 3) * esc, by + 3 * esc, esc, esc)

    def draw_world(self):
        w, cw = self.world, self.chars
        cw.fill((0, 0, 0, 0))
        if self.scene == "ext":
            w.blit(self.bg_ext, (0, 0))
            dibujar_buzon(cw, BUZON_X, GROUND + 1, self.t, self.buzon_nuevo)
            self._dibujar_jugador_lado(cw)
        elif self.scene == "map":
            cx, cy = self.cam_mapa()
            w.blit(self.plano, (0, 0), (cx, cy, W, H))
            lista = []                                  # se dibuja de arriba hacia abajo para que se tapen bien
            for n in NPCS:
                nx, ny = self.map_pos(n["id"])
                dx, dy, voltear = self._pose(n)
                im = self.npc_front[n["id"]]
                if voltear:
                    im = pygame.transform.flip(im, True, False)
                lista.append((ny, n, im, nx - cx + dx, ny - cy, dy))
            lista.append((self.my, None, self.map_player[self.mdir][self.frame], self.mx - cx, self.my - cy, 0))
            for _, n, im, x, y, dy in sorted(lista, key=lambda e: e[0]):
                cw.blit(self._sombra_mapa, (int(x) + 9, int(y) + 29))
                cw.blit(im, (int(x), int(y) + dy))
            for _, n, im, x, y, dy in lista:
                if n is not None:
                    self._particulas(cw, n, x + 16, y + dy, 1)
        else:                                           # sala de perfil
            w.blit(self.salas[self.sala], (0, 0))
            info = SALAS[self.sala]
            n = self.npc_by_id[info["npc"]]
            dx, dy, voltear = self._pose(n)
            if voltear is None:                         # mira hacia ti
                voltear = self.px + SPRITE / 2 > info["x"] + SPRITE / 2
            img = self.npc_sprites[n["id"]]
            if voltear:
                img = pygame.transform.flip(img, True, False)
            x = info["x"] + dx * 2
            self._shadow(cw, x + SPRITE // 2, GROUND + 1)
            cw.blit(img, (x, GROUND - FEET + dy * 2))
            self._particulas(cw, n, x + SPRITE // 2, GROUND - FEET + dy * 2, 2)
            self._dibujar_jugador_lado(cw)

    # --- barra superior ---------------------------------------------------
    def _ui_barra(self, s, zona):
        ui_rect(s, (0, 0, 0, 70), 0, 22, W, 2)                  # sombra bajo la barra
        ui_rect(s, UI_FONDO, 0, 0, W, 20)
        ui_rect(s, UI_FONDO2, 0, 1, W, 1)
        ui_rect(s, UI_ORO, 0, 20, W, 1)
        ui_rect(s, UI_LINEA, 0, 21, W, 1)
        # insignia del hospital (cruz roja sobre blanco)
        ui_rect(s, UI_LINEA, 4, 3, 14, 14)
        ui_rect(s, (245, 248, 250), 5, 4, 12, 12)
        ui_rect(s, (214, 58, 58), 9, 5, 4, 10)
        ui_rect(s, (214, 58, 58), 6, 8, 10, 4)
        # nombre de la zona
        s.blit(ui_texto(zona, UI_CREMA), (24, 5))
        # retratos de los 8 stakeholders (progreso)
        total = len(NPCS)
        cont = ui_texto(f"{len(self.collected)}/{total}", UI_ORO)
        x0 = W - 6 - cont.get_width() - 6 - total * 21
        for i, n in enumerate(NPCS):
            x = x0 + i * 21
            ok = n["id"] in self.collected
            borde = UI_ORO if ok else (62, 78, 116)
            if ok and self.collected[-1] == n["id"] and self.banner_t > 100 and (self.t // 6) % 2 == 0:
                borde = (255, 255, 255)                         # destello al identificar a alguien
            ui_rect(s, UI_LINEA, x, 1, 20, 18)
            ui_rect(s, borde, x + 1, 2, 18, 16)
            ui_rect(s, (30, 42, 74) if not ok else (58, 74, 118), x + 2, 3, 16, 14)
            s.blit(self.caras[n["id"]] if ok else self.siluetas[n["id"]], (x + 2, 3))
        s.blit(cont, (W - 6 - cont.get_width(), 5))

    # --- panel de stakeholders (poder / interés) -----------------------------
    def _ui_panel(self, s):
        if not self.panel_visible:
            return
        w, tx = 162, 25                                         # ancho del panel y dónde empieza el texto
        ancho_txt = w - tx - 6
        cuantos = 1 if self.scene == "sala" else 3              # en las salas solo el último (para no tapar a nadie)
        ultimos = self.collected[-cuantos:]                     # se muestran los más recientes
        alto = 20
        if not self.collected:
            hint = ui_partir("Entra a cada sala y conoce a la persona", w - 14)
            alto += 10 * len(hint) + 4
        else:
            if len(self.collected) > len(ultimos):
                alto += 10
            alto += 35 * len(ultimos)
        x, y = W - w - 4, 28
        ui_marco(s, x, y, w, alto)
        ui_rect(s, UI_FONDO2, x + 3, y + 3, w - 6, 13)          # franja del título
        ui_rect(s, UI_ORO_OSC, x + 3, y + 16, w - 6, 1)
        s.blit(ui_texto("STAKEHOLDERS", UI_ORO), (x + 8, y + 3))
        num = ui_texto(f"{len(self.collected)}/{len(NPCS)}", UI_CREMA)
        s.blit(num, (x + w - 8 - num.get_width(), y + 3))
        yy = y + 20
        if not self.collected:
            for l in hint:
                s.blit(ui_texto(l, UI_GRIS), (x + 7, yy))
                yy += 10
            return
        if len(self.collected) > len(ultimos):
            s.blit(ui_texto(f"+{len(self.collected) - len(ultimos)} ANTERIORES", UI_GRIS), (x + 8, yy))
            yy += 10
        for k, nid in enumerate(ultimos):
            n = self.npc_by_id[nid]
            nuevo = (k == len(ultimos) - 1 and self.banner_t > 100)
            ui_rect(s, UI_LINEA, x + 5, yy - 1, 18, 17)         # carita
            ui_rect(s, UI_ORO if nuevo else UI_ORO_OSC, x + 6, yy, 16, 15)
            ui_rect(s, (58, 74, 118), x + 6, yy + 1, 16, 14)
            s.blit(self.caras[nid], (x + 6, yy + 1))
            s.blit(ui_texto(ui_cortar(n["name"], ancho_txt), UI_ORO), (x + tx, yy - 1))
            px = x + tx                                         # PODER ▮▮▮  INTERÉS ▮▮▯
            s.blit(ui_texto("PODER", UI_GRIS), (px, yy + 9))
            px += ui_ancho("PODER") + 4
            px += ui_medidor(s, px, yy + 11, n.get("poder", "")) + 7
            s.blit(ui_texto("INTERÉS", UI_GRIS), (px, yy + 9))
            px += ui_ancho("INTERÉS") + 4
            ui_medidor(s, px, yy + 11, n.get("interes", ""))
            cuad = n.get("cuadrante", "")
            s.blit(ui_texto(ui_cortar(cuad, ancho_txt), COLOR_CUADRANTE.get(cuad, UI_CREMA)), (x + tx, yy + 20))
            yy += 35
            if k < len(ultimos) - 1:
                for dx in range(x + 6, x + w - 6, 3):            # línea punteada entre stakeholders
                    s.set_at((dx, yy - 4), (62, 78, 116))

    # --- globos de los stakeholders -----------------------------------------
    def _ui_globo(self, s, cx, top, lineas, borde=UI_ORO, feet=None):
        """Globo pixel art sobre la cabeza (o debajo si no cabe). lineas = [(texto, color), ...]"""
        cx, top = int(cx), int(top)
        bw = max(ui_ancho(t) for t, _ in lineas) + 12
        bh = 10 * len(lineas) + 7
        x = max(4, min(W - bw - 4, cx - bw // 2))
        y = top - bh - 6
        arriba = True
        if feet is not None and y < 26:                         # si no cabe arriba, va debajo del personaje
            y, arriba = int(feet) + 6, False
        ui_marco(s, x, y, bw, bh, borde=borde, fondo=(18, 24, 44))
        tx = max(x + 7, min(x + bw - 8, cx))
        for r in range(4):                                      # colita triangular
            yo = (y + bh - 2 + r) if arriba else (y + 1 - r)
            ui_rect(s, borde, tx - (3 - r), yo, 2 * (3 - r) + 1, 1)
            if r < 3:
                ui_rect(s, (18, 24, 44), tx - (2 - r), yo, 2 * (2 - r) + 1, 1)
        for i, (t, c) in enumerate(lineas):
            s.blit(ui_texto(t, c), (x + 6, y + 3 + 10 * i))

    def _ui_globo_stakeholder(self, s, n, cx, top, feet, en_mapa):
        conflict = n.get("conflict")
        if conflict and not self.c_resolved[conflict] and (self.c_alpha[conflict] > 0.5 if en_mapa else self.npc_alpha[n["id"]] > 0.5):
            lin = [(t, (255, 214, 200)) for t in ui_partir(n["says"], 150)] + [(n["name"], UI_ORO)]
            self._ui_globo(s, cx, top, lin, borde=UI_ROJO, feet=feet)
        elif self.npc_alpha[n["id"]] > 0.5:
            lin = [(t, UI_CREMA) for t in ui_partir(n["name"], 150)] + [(t, UI_ORO) for t in ui_partir(n["role"], 150)]
            self._ui_globo(s, cx, top, lin, feet=feet)
        elif n["id"] in self.collected:
            ui_icono(s, int(cx) - 4, int(top) - 12, ICONO_OK, PAL_OK)    # marca de "identificado"

    def _ui_rayo(self, s, cx, cy):
        """Rayito de conflicto entre dos stakeholders (se usará en el capítulo de conflictos)."""
        if (self.t // 8) % 4 != 3:
            ui_icono(s, int(cx) - 4, int(cy) - 5, ICONO_RAYO, PAL_RAYO)

    # --- "Presione E" y ayuda de teclas ----------------------------------------
    def _ui_prompt(self, s, antes, tecla, despues):
        """Cartel de abajo: 'Presione [E] para entrar'."""
        a, b = ui_texto(antes, UI_CREMA), ui_texto(despues, UI_CREMA)
        bw = a.get_width() + b.get_width() + ui_ancho(tecla) + 6 + 28
        x, y = (W - bw) // 2, H - 36
        ui_marco(s, x, y, bw, 20)
        pulsada = (self.t // 24) % 2 == 1                       # la tecla sube y baja para llamar la atención
        s.blit(a, (x + 9, y + 6))
        kx = x + 9 + a.get_width() + 5
        ui_tecla(s, kx, y + 4, tecla, pulsada)
        s.blit(b, (kx + ui_ancho(tecla) + 6 + 5, y + 6))

    def _ui_tecla_flotante(self, s, cx, top):
        """Teclita E que flota sobre la cabeza de tu personaje cuando puedes usar la puerta."""
        dy = int(math.sin(self.t * 0.12) * 2)
        x = int(cx) - 6
        y = int(top) - 22 + dy
        ui_tecla(s, x, y, "E")
        ui_rect(s, UI_LINEA, int(cx) - 2, y + 13, 5, 1)
        ui_rect(s, UI_LINEA, int(cx) - 1, y + 14, 3, 1)
        ui_rect(s, UI_LINEA, int(cx), y + 15, 1, 1)

    def _ui_ayuda(self, s, mapa):
        """Cuadrito abajo a la izquierda con las teclas (arriba: moverte, medio: correr, abajo: panel)."""
        teclas = ("W", "A", "S", "D") if mapa else ("A", "D")
        filas = (3 if self.scene != "ext" else 2) + 1
        w_mover = 8 + len(teclas) * 13 + ui_ancho("MOVER") + 6
        activo = getattr(self, "correr_toggle", False)
        txt_correr = "CORRER (ON)" if activo else "CORRER"
        w_correr = 10 + ui_ancho("SHIFT") + 6 + 5 + ui_ancho(txt_correr) + 6
        w = max(w_mover, w_correr, 10 + ui_ancho("M") + 13 + ui_ancho("SONIDO (NO)") + 6)
        alto = 6 + 14 * filas
        ui_marco(s, 4, H - 4 - alto, w, alto, borde=(62, 78, 116), brillo=False)
        y = H - 4 - alto + 4
        x = 10
        for k in teclas:
            x += ui_tecla(s, x, y, k) + 2
        s.blit(ui_texto("MOVER", UI_GRIS), (x + 3, y + 2))

        # Fila correr: SHIFT o C
        y += 14
        kx = ui_tecla(s, 10, y, "SHIFT")
        col = UI_ORO if activo else UI_GRIS
        s.blit(ui_texto(txt_correr, col), (10 + kx + 5, y + 2))

        # Fila panel
        if self.scene != "ext":
            y += 14
            kx = ui_tecla(s, 10, y, "TAB")
            s.blit(ui_texto("PANEL", UI_GRIS), (10 + kx + 5, y + 2))

        # Fila sonido
        y += 14
        voz = getattr(self, "_voz", None)
        suena = True if voz is None else voz.activo
        kx = ui_tecla(s, 10, y, "M")
        s.blit(ui_texto("SONIDO" if suena else "SONIDO (NO)", UI_GRIS if suena else UI_ORO), (10 + kx + 5, y + 2))

    # --- avisos, misión y logro ------------------------------------------------
    def _ui_aviso(self, s):
        """Cinta de aviso arriba: baja, se queda un rato y vuelve a subir."""
        if self.banner_t <= 0:
            return
        texto = self.banner
        if texto.startswith("Resuelto"):
            borde, icono, pal = UI_VERDE, ICONO_OK, PAL_OK
        elif texto.startswith("Conflicto"):
            borde, icono, pal = UI_ROJO, ICONO_RAYO, PAL_RAYO
        elif texto.startswith(("¡Recorrido", "¡Misión", "Capítulo")):
            borde, icono, pal = UI_ORO, ICONO_ESTRELLA, PAL_ESTRELLA
        elif "identificad" in texto:
            borde, icono, pal = UI_ORO, ICONO_OK, PAL_OK
        else:
            borde, icono, pal = UI_ORO, None, None
        con_panel = self.scene != "ext" and self.panel_visible      # si el panel está abierto, el aviso va a su izquierda
        iw = 15 if icono else 0
        lin = ui_partir(texto, (186 if con_panel else 250) - iw)
        bw = max(ui_ancho(l) for l in lin) + 16 + iw
        bh = 10 * len(lin) + 10
        x = max(4, ((W - 170) if con_panel else W) // 2 - bw // 2)
        y = 28 if self.logro_t <= 0 else 60                     # si está el logro arriba, el aviso baja un poco
        if self.banner_t > 158:                                 # entra deslizando desde arriba
            y -= (self.banner_t - 158) * 4
        elif self.banner_t < 12:                                # y se va hacia arriba
            y -= (12 - self.banner_t) * 4
        ui_marco(s, x, y, bw, bh, borde=borde, fondo=(18, 24, 44))
        if icono:
            ui_icono(s, x + 7, y + (bh - 9) // 2, icono, pal)
        for i, l in enumerate(lin):
            s.blit(ui_texto(l, UI_CREMA), (x + 8 + iw, y + 5 + 10 * i))

    def _ui_mision(self, s):
        """Cartel de la misión del capítulo (solo en la calle, mientras no hay aviso)."""
        if self.banner_t > 0 or self.menu is not None:
            return
        if self.buzon_nuevo:
            lin = [("¡MISIÓN CUMPLIDA!", UI_ORO), ("Revisa el buzón", UI_CREMA), ("de la izquierda", UI_CREMA)]
        elif len(self.collected) < len(NPCS):
            cap = CAPITULOS[self.capitulo - 1]
            lin = [(f"CAPÍTULO {self.capitulo}", UI_ORO)] + [(l, UI_CREMA) for l in ui_partir(cap["mision"], 100)] \
                  + [(f"Llevas {len(self.collected)}/{len(NPCS)}", UI_GRIS)]
        else:
            return
        bw = max(ui_ancho(l) for l, _ in lin) + 16
        ui_marco(s, 4, 28, bw, 10 * len(lin) + 8)
        for i, (l, c) in enumerate(lin):
            s.blit(ui_texto(l, c), (12, 32 + 10 * i))

    def _ui_logro(self, s):
        """Recuadro de '¡Logro obtenido!' que entra por la derecha (como en Minecraft)."""
        if self.logro_t <= 0:
            return
        self.logro_t -= 1
        t1, t2 = "¡LOGRO OBTENIDO!", self.logro_txt
        bw = max(ui_ancho(t1), ui_ancho(t2)) + 36
        x, y = W - bw - 4, 26
        if self.logro_t > 280:                                  # entra desde la derecha
            x += (self.logro_t - 280) * 10
        elif self.logro_t < 16:                                 # y se va por la derecha
            x += (16 - self.logro_t) * 14
        ui_marco(s, x, y, bw, 30, borde=(150, 150, 162), fondo=(40, 40, 48))
        ui_rect(s, (24, 24, 30), x + 5, y + 5, 19, 20)          # cuadrito del icono
        ui_icono(s, x + 10, y + 10, ICONO_TROFEO, PAL_TROFEO)
        s.blit(ui_texto(t1, (255, 255, 85)), (x + 29, y + 4))
        s.blit(ui_texto(t2, (255, 255, 255)), (x + 29, y + 15))

    # --- menú del buzón -------------------------------------------------------
    def _ui_menu(self, s):
        if self.menu is None:
            return
        ui_rect(s, (0, 0, 0, 140), 0, 0, W, H)                  # oscurece el fondo
        bw, bh = 262, 22 + 27 * len(CAPITULOS) + 22
        x, y = (W - bw) // 2, (H - bh) // 2
        ui_marco(s, x, y, bw, bh)
        ui_rect(s, UI_FONDO2, x + 3, y + 3, bw - 6, 13)
        ui_rect(s, UI_ORO_OSC, x + 3, y + 16, bw - 6, 1)
        s.blit(ui_texto("BUZÓN · CAPÍTULOS", UI_ORO), (x + 8, y + 3))
        for i, cap in enumerate(CAPITULOS):
            ry = y + 21 + i * 27
            libre = i < self.desbloqueados
            elegido = libre and i == self.menu["sel"]
            ui_rect(s, (48, 64, 106) if elegido else (28, 38, 66), x + 6, ry, bw - 12, 24)
            if elegido:                                         # marco dorado y flechita que se mueve
                for rx, rw in ((x + 6, bw - 12),):
                    ui_rect(s, UI_ORO, rx, ry, rw, 1)
                    ui_rect(s, UI_ORO, rx, ry + 23, rw, 1)
                ui_rect(s, UI_ORO, x + 6, ry, 1, 24)
                ui_rect(s, UI_ORO, x + bw - 7, ry, 1, 24)
                fx = x + 10 + (self.t // 15) % 2
                for k in range(4):
                    ui_rect(s, UI_ORO, fx + k, ry + 8 + k, 1, 8 - 2 * k)
            bx = x + 18                                         # numerito del capítulo
            ui_rect(s, UI_LINEA, bx, ry + 4, 16, 16)
            ui_rect(s, UI_ORO if libre else (70, 78, 100), bx + 1, ry + 5, 14, 14)
            s.blit(ui_texto(str(i + 1), UI_FONDO, None), (bx + 5, ry + 6))
            if libre:
                s.blit(ui_texto(f"CAPÍTULO {i + 1}", UI_ORO), (x + 40, ry + 2))
                s.blit(ui_texto(cap["titulo"], UI_CREMA), (x + 40, ry + 12))
                if cap.get("logro") and cap["logro"] in self.logros:
                    ui_icono(s, x + bw - 20, ry + 8, ICONO_OK, PAL_OK)        # capítulo completado
                elif i > 0 and (self.t // 20) % 3 != 0:
                    s.blit(ui_texto("NUEVO", (255, 255, 85)), (x + bw - 44, ry + 2))
            else:
                ui_icono(s, x + 40, ry + 8, ICONO_CANDADO, PAL_CANDADO)
                s.blit(ui_texto("???", UI_GRIS), (x + 52, ry + 7))
        hy = y + bh - 19                                        # ayuda de teclas del menú
        hx = x + 10
        for k in ("W", "S"):
            hx += ui_tecla(s, hx, hy, k) + 2
        s.blit(ui_texto("ELEGIR", UI_GRIS), (hx + 3, hy + 2))
        hx += ui_ancho("ELEGIR") + 12
        hx += ui_tecla(s, hx, hy, "E") + 4
        s.blit(ui_texto("ABRIR", UI_GRIS), (hx, hy + 2))
        hx += ui_ancho("ABRIR") + 10
        hx += ui_tecla(s, hx, hy, "ESC") + 4
        s.blit(ui_texto("CERRAR", UI_GRIS), (hx, hy + 2))

    # --- dibujo principal de la interfaz -------------------------------------
    def _ui_actores(self, s):
        """Globos de los stakeholders, marcas de 'identificado' y rayo de conflicto."""
        if self.scene == "map":
            cx, cy = self.cam_mapa()
            for n in NPCS:
                nx, ny = self.map_pos(n["id"])
                dx, dy, _ = self._pose(n)
                sx, top, feet = nx + 16 - cx + dx, ny - cy + dy, ny + 30 - cy
                if 0 <= sx <= W and 0 <= feet <= H:
                    self._ui_globo_stakeholder(s, n, sx, top, feet, True)
            for k, c in CONFLICTS.items():
                if self.c_alpha[k] > 0.3 and not self.c_resolved[k]:
                    a, b = (self.npc_by_id[i] for i in c["members"])
                    ax, ay = self.map_pos(a["id"])
                    bx, by = self.map_pos(b["id"])
                    self._ui_rayo(s, (ax + bx) / 2 + 16 - cx, (ay + by) / 2 + 8 - cy + math.sin(self.t * 0.2) * 2)
        elif self.scene == "sala":
            info = SALAS[self.sala]
            n = self.npc_by_id[info["npc"]]
            dx, dy, _ = self._pose(n)
            self._ui_globo_stakeholder(s, n, info["x"] + dx * 2 + SPRITE / 2, GROUND - FEET + dy * 2, None, False)

    def draw_ui(self, screen):
        self._ui_init()
        s = self.ui
        s.fill((0, 0, 0, 0))
        quien = None                                            # (x, y de la cabeza de tu personaje) para la teclita
        pregunta = None                                         # texto del cartel "Presione E"
        libre = self.trans is None and self.menu is None
        if self.scene == "ext":
            zona = "Exterior · Centro de salud"
            if libre and self.near_door():
                pregunta = "ENTRAR"
            elif libre and self.cerca_buzon():
                pregunta = "VER CAPÍTULOS"
        elif self.scene == "map":
            cx, cy = self.cam_mapa()
            zona = "Centro de salud"
            quien = (self.mx + 16 - cx, self.my - cy)
            if libre and not self.lock_door and self._puerta_actual():
                pregunta = "ENTRAR"
            elif libre and self.en_salida():
                pregunta = "SALIR"
        else:
            zona = SALAS[self.sala]["name"]
            quien = (self.px + SPRITE / 2, GROUND - FEET)
            if libre and self.px < 34:
                pregunta = "SALIR"

        self._ui_barra(s, zona)
        if self.scene == "ext":
            self._ui_mision(s)
        else:
            self._ui_panel(s)
        self._ui_actores(s)
        self._ui_aviso(s)
        if pregunta:
            if quien:
                self._ui_tecla_flotante(s, quien[0], quien[1])
            self._ui_prompt(s, "PRESIONE", "E", "PARA " + pregunta)
        if self.menu is None:
            self._ui_ayuda(s, self.scene == "map")
        self._ui_logro(s)
        self._ui_menu(s)
        screen.blit(pygame.transform.scale(s, (SCREEN_W, SCREEN_H)), (0, 0))

    def render(self, screen):
        self._ui_init()
        self.draw_world()
        pygame.transform.scale(self.world, (SCREEN_W, SCREEN_H), screen)
        if self.scene == "ext":
            screen.blit(self.hospital["open" if self.door_open else "closed"], (self.hosp_x, self.hosp_y))
        screen.blit(pygame.transform.scale(self.chars, (SCREEN_W, SCREEN_H)), (0, 0))
        self.draw_ui(screen)
        if self.fade > 0:                                       # fundido a negro
            self._fade_surf.set_alpha(int(255 * self.fade))
            screen.blit(self._fade_surf, (0, 0))
    # ======================== FIN DEL BLOQUE C ========================

    # ======================================================================
    # CAPÍTULOS 2 Y 3 (diálogos con retrato, tarjetas, decisiones, hilo dorado)
    # ======================================================================
    _update_c1 = update
    _tecla_c1 = tecla
    _press_e_c1 = press_e
    _recoger_c1 = _recoger
    _ui_panel_c1 = _ui_panel
    _ui_mision_c1 = _ui_mision

    def _c23(self):
        """Prepara el estado de los capítulos 2 y 3 (se llama sola)."""
        if hasattr(self, "modal"):
            return
        self._ui_init()
        self.modal = None                 # ventana de diálogo / tarjeta / elección abierta
        self.c2 = dict(modulos=False)
        self.c3 = dict(inicio=False, puertas=0, fin=False, cierre=False)
        self._retratos = {}

    # --- quién está dónde ---------------------------------------------------
    def _visita(self, nid):
        return VISITAS.get(self.capitulo, {}).get(nid) if hasattr(self, "capitulo") else None

    def _donde(self, nid):
        v = self._visita(nid)
        return v[0] if v else self.room_of_npc[nid]

    def map_pos(self, npc_id):
        v = self._visita(npc_id)
        return v[1] if v else SALAS[self.room_of_npc[npc_id]]["map_pos"]

    def _sala_x(self, nid):
        v = self._visita(nid)
        return v[2] if v else SALAS[self.room_of_npc[nid]]["x"]

    def _presentes(self, sala):
        return [n for n in NPCS if self._donde(n["id"]) == sala]

    def _cerca_en_sala(self):
        """El stakeholder de la sala que está más cerca de ti (o None si nadie está cerca)."""
        mejor, dist = None, PROX
        for n in self._presentes(self.sala):
            d = abs(self.px + SPRITE / 2 - (self._sala_x(n["id"]) + SPRITE / 2))
            if d < dist:
                mejor, dist = n, d
        return mejor

    def _update_sala(self):
        for n in self._presentes(self.sala):
            near = abs((self.px + SPRITE / 2) - (self._sala_x(n["id"]) + SPRITE / 2)) < PROX
            self.npc_alpha[n["id"]] += ((1 if near else 0) - self.npc_alpha[n["id"]]) * 0.18
            if near and n["id"] not in self.collected:
                self._recoger(n)

    # --- ventana modal: diálogo, tarjeta, elección ----------------------------
    def _abrir_modal(self, paginas, al_terminar=None):
        self.modal = dict(paginas=paginas, i=0, t=0, sel=0, fin=al_terminar, msg=None,
                          elegidos=set(), bloq=set(), tachadas=set())

    def _modal_siguiente(self):
        m = self.modal
        m["i"] += 1
        m["t"], m["sel"], m["msg"] = 0, 0, None
        m["elegidos"], m["bloq"], m["tachadas"] = set(), set(), set()
        if m["i"] >= len(m["paginas"]):
            fin = m["fin"]
            self.modal = None
            if fin:
                fin()

    def _texto_dialogo(self, p):
        return ui_partir(p["texto"], 270)

    def _modal_tecla(self, key):
        m = self.modal
        p = m["paginas"][m["i"]]
        tipo = p["tipo"]
        sigue = key in (pygame.K_e, pygame.K_RETURN, pygame.K_SPACE)
        arriba = key in (pygame.K_w, pygame.K_UP)
        abajo = key in (pygame.K_s, pygame.K_DOWN)
        if tipo == "dialogo":
            total = sum(len(l) for l in self._texto_dialogo(p))
            if sigue:
                if m["t"] * TEXTO_VEL < total:
                    m["t"] = 9999                               # muestra todo el texto de golpe
                else:
                    self._modal_siguiente()
        elif tipo in ("tarjeta", "fin"):
            if sigue and m["t"] > 8:
                self._modal_siguiente()
        elif tipo == "apagon":
            if sigue and m["t"] > 30:
                self._modal_siguiente()
        elif tipo == "modulos":
            if arriba:
                m["sel"] = (m["sel"] - 1) % len(MODULOS)
            elif abajo:
                m["sel"] = (m["sel"] + 1) % len(MODULOS)
            elif sigue:
                if len(m["elegidos"]) >= 2:
                    self._modal_siguiente()
                    return
                i = m["sel"]
                mod = MODULOS[i]
                if i in m["elegidos"] or i in m["bloq"]:
                    return
                if mod["ok"]:
                    m["elegidos"].add(i)
                    m["msg"] = (mod["nota"], UI_VERDE)
                else:
                    m["bloq"].add(i)
                    m["msg"] = (mod["nota"], UI_ROJO)
                if len(m["elegidos"]) >= 2:
                    m["msg"] = ("¡Bien! Las 2 monedas van a los Must have. Presiona E para continuar.", UI_ORO)
        elif tipo == "abrir":
            if p.get("abierto"):
                if sigue:
                    self._modal_siguiente()
            elif key in (pygame.K_a, pygame.K_d, pygame.K_LEFT, pygame.K_RIGHT) or arriba or abajo:
                m["sel"] = 1 - m["sel"]
            elif sigue and m["t"] > 8:
                if m["sel"] == 1:
                    self._modal_siguiente()
                else:
                    nombre = DIAGRAMAS[p["clave"]][1]
                    ruta = buscar_diagrama(p["clave"])
                    if ruta and abrir_archivo(ruta):
                        p["abierto"] = True
                        m["msg"] = ("ABIERTO EN OTRA VENTANA. CUANDO TERMINES, VUELVE AL JUEGO Y PRESIONA E.", UI_VERDE)
                    else:
                        m["msg"] = (f"NO ENCUENTRO EL ARCHIVO. GUARDA UNO LLAMADO {nombre} (PNG, PDF...) EN LA CARPETA "
                                    "DIAGRAMAS DEL JUEGO. CON NO SIGUES SIN ABRIRLO.", UI_ROJO)
        elif tipo == "alternativas":
            conf = CONFLICTOS_C2[p["conf"]]
            n = len(conf["alternativas"])
            if arriba:
                m["sel"] = (m["sel"] - 1) % n
            elif abajo:
                m["sel"] = (m["sel"] + 1) % n
            elif sigue:
                letra, nombre, notas, total, motivo = conf["alternativas"][m["sel"]]
                if motivo is None:
                    self._modal_siguiente()
                else:
                    m["tachadas"].add(m["sel"])
                    m["msg"] = (f"{letra} ({total:.2f}) · {motivo}", UI_ROJO)

    # --- teclas, actualización y tecla E -------------------------------------
    def tecla(self, key):
        self._c23()
        if self.modal is not None:
            self._modal_tecla(key)
            return None
        return self._tecla_c1(key)

    def update(self, left, right, up=False, down=False, run=False):
        self._c23()
        if self.modal is not None:
            m = self.modal
            m["t"] += 1
            self._sonar_voz(m)
            if m["paginas"][m["i"]]["tipo"] == "apagon" and m["t"] > 120:
                self._modal_siguiente()
            left = right = up = down = run = False
        self._update_c1(left, right, up, down, run)
        # Capítulo 1: cuando se va el logro, sale el cartel de los supuestos
        if getattr(self, "_supuestos_pend", False) and self.logro_t <= 20 and self.modal is None and self.trans is None:
            self._supuestos_pend = False
            self._abrir_modal(self._paginas_supuestos())
        # cierre del juego: al salir a la calle después del Capítulo 3
        if (self.scene == "ext" and self.trans is None and self.modal is None and self.capitulo == 3
                and self.c3["fin"] and not self.c3["cierre"]):
            self.c3["cierre"] = True
            self._abrir_modal(self._paginas_cierre())

    def _sonar_voz(self, m):
        """Cada letra nueva del diálogo hace un 'blip' con la voz del que habla."""
        p = m["paginas"][m["i"]]
        if p["tipo"] != "dialogo":
            return
        if not hasattr(self, "_voz"):
            self._voz = Voces()
        texto = "".join(self._texto_dialogo(p))
        antes = min(int((m["t"] - 1) * TEXTO_VEL), len(texto))
        ahora = min(int(m["t"] * TEXTO_VEL), len(texto))
        if ahora - antes > 6:                                   # se saltó el texto de golpe: sin sonido
            return
        for ch in texto[antes:ahora]:
            if ch.isalnum():
                self._voz.letra(p["quien"])

    def _tarea_sala(self):
        """Qué se puede hacer con E en esta sala (según el capítulo), si estás cerca de alguien."""
        if self.scene != "sala" or self._cerca_en_sala() is None:
            return None
        if self.capitulo == 2:
            t = TAREA_DE_SALA.get(self.sala)
            if t == "modulos" and not self.c2["modulos"]:
                return t
            if t in CONFLICTS and not self.c_resolved[t]:
                return t
        if self.capitulo == 3 and self.sala == "admision" and not self.c3["inicio"]:
            return "hilo"
        return None

    def press_e(self):
        self._c23()
        if self.trans is not None:
            return
        tarea = self._tarea_sala()
        if tarea == "modulos":
            self._abrir_modal(self._paginas_modulos(), self._fin_modulos)
            return
        if tarea in CONFLICTS:
            self._abrir_modal(self._paginas_conflicto(tarea), lambda k=tarea: self._fin_conflicto(k))
            return
        if tarea == "hilo":
            self._abrir_modal(self._paginas_inicio_hilo(), self._fin_inicio_hilo)
            return
        if self.scene == "map" and self.capitulo == 3 and self.c3["inicio"]:
            i = self._puerta_hilo_cerca()
            if i is not None:
                self._abrir_puerta(i)
                return
        self._press_e_c1()

    # --- capítulos ------------------------------------------------------------
    def _elegir_capitulo(self):
        self._c23()
        sel = self.menu["sel"]
        self.menu = None
        self.capitulo = sel + 1
        for k in self.npc_alpha:
            self.npc_alpha[k] = 0.0
        if self.capitulo == 1:
            self.collected = []
            self._apagar_conflictos()
        else:
            self.collected = [n["id"] for n in NPCS]
            if self.capitulo == 2:
                self.c2 = dict(modulos=False)
                for k in CONFLICTS:
                    self.c_resolved[k], self.c_shown[k], self.c_alpha[k] = False, False, 0.0
            else:
                self.c3 = dict(inicio=False, puertas=0, fin=False, cierre=False)
                self._apagar_conflictos()
        self.show_banner(f"Capítulo {self.capitulo}: " + CAPITULOS[sel]["titulo"])

    def _recoger(self, n):
        self._recoger_c1(n)
        if self.capitulo == 1 and len(self.collected) == len(NPCS):
            self._supuestos_pend = True

    def _paginas_supuestos(self):
        return [dict(
                tipo="tarjeta", titulo="LO QUE EL CASO NO DECÍA: NUESTROS SUPUESTOS", fuente="Tabla 2 y sección 1.4",
                lineas=[("El caso no decía todo, así que tomamos decisiones y las dejamos escritas:", UI_GRIS)]
                + [(f"{i + 1}. {t}", UI_CREMA) for i, t in enumerate(SUPUESTOS)])]

    def _progreso_c2(self):
        return int(self.c2["modulos"]) + sum(1 for k in CONFLICTS if self.c_resolved[k])

    def _revisar_fin_c2(self):
        if self.capitulo == 2 and self._progreso_c2() == 1 + len(CONFLICTS):
            self._logro(CAPITULOS[1]["logro"])
            self.desbloqueados = max(self.desbloqueados, 3)
            self.buzon_nuevo = True
            self.show_banner("¡Misión cumplida! Sal del centro de salud y revisa el buzón")

    # --- Capítulo 2: los módulos ---------------------------------------------
    def _paginas_modulos(self):
        return [
            dict(tipo="dialogo", quien="arian", emo="neutral", texto="Buenos días, soy Arian, de Administración. Vengo a hablar del presupuesto."),
            dict(tipo="dialogo", quien="arian", emo="preocupado", texto="El presupuesto de la DIRESA solo alcanza para 2 de los 5 módulos."),
            dict(tipo="dialogo", quien="arian", emo="pensativo", texto="Tienes 2 monedas. ¿En qué módulos las pondrías?"),
            dict(tipo="modulos"),
            dict(tipo="tarjeta", titulo="MOSCOW: QUÉ ENTRA EN LA PRIMERA FASE", fuente="Tabla 14 y sección 2.7",
                 lineas=[("MoSCoW fue el filtro para respetar el presupuesto de 2 de 5 módulos:", UI_GRIS),
                         ("MUST: Historia clínica y receta (HU-001 a HU-005), auditoría (HU-007) y usuarios (HU-008).", UI_VERDE),
                         ("SHOULD: Dispensar la receta (HU-006), dentro del mismo módulo.", (120, 200, 255)),
                         ("COULD: Derivaciones (HU-010) → Fase 2.", (255, 196, 90)),
                         ("WON'T (esta vez): Gestión completa de inventario (HU-009) → Fase 2.", UI_ROJO)]),
            dict(tipo="tarjeta", titulo="WSJF: EN QUÉ ORDEN SE CONSTRUYE", fuente="Tabla 14",
                 lineas=[("WSJF = costo del retraso / tamaño. Ordena las historias Must para cada sprint:", UI_GRIS)],
                 dibujo=self._dibujo_wsjf),
            dict(tipo="tarjeta", titulo="TÉCNICA DESCARTADA: VALOR VS. ESFUERZO", fuente="Tabla 13", icono="puerta",
                 lineas=[("También probamos la matriz Valor vs. Esfuerzo, pero la descartamos:", UI_CREMA),
                         ("· No garantiza cumplir la norma obligatoria (NTS 139).", UI_ROJO),
                         ("· No da un cálculo para ordenar el backlog.", UI_ROJO),
                         ("Por eso usamos MoSCoW + WSJF juntos.", UI_VERDE)]),
            dict(tipo="tarjeta", titulo="CONTROL DE CAMBIOS · CR-002", fuente="Tabla 39",
                 lineas=[("Cuando el alcance cambió, lo dejamos registrado (v1.1 → v1.2):", UI_GRIS),
                         ("Derivaciones (RF-009, RF-012 y RF-013) pasan a Could have y se van a la Fase 2.", UI_CREMA),
                         ("El CU-010 queda fuera de la primera fase.", UI_CREMA),
                         ("Así nos concentramos en los 2 módulos: Historia Clínica Electrónica y Receta Electrónica/Farmacia.", UI_VERDE),
                         ("Disparador: el presupuesto cubre solo 2 de 5 módulos. Impacto: se reduce el alcance y el tiempo "
                          "(aprox. -3 días de trabajo).", UI_ORO),
                         ("Aprobado por los stakeholders (Administración y MINSA), acta del 02/11/2026.", UI_GRIS)]),
            dict(tipo="dialogo", quien="arian", emo="contento",
                 texto="Con MoSCoW decidimos qué entra y con WSJF en qué orden se construye. ¡Decisión tomada!"),
        ]

    def _fin_modulos(self):
        self.c2["modulos"] = True
        self.show_banner("Resuelto: módulos priorizados (HCE y Receta Electrónica)")
        self._revisar_fin_c2()

    def _dibujo_wsjf(self, s, x, y, w):
        maxv = max(v for _, _, v in WSJF)
        for i, (hu, nombre, v) in enumerate(WSJF):
            yy = y + i * 11
            s.blit(ui_texto(hu, UI_ORO if i == 0 else UI_GRIS), (x, yy))
            s.blit(ui_texto(ui_cortar(nombre, 168), UI_CREMA), (x + 42, yy))
            bw = int((w - 254) * v / maxv)
            ui_rect(s, UI_LINEA, x + 214, yy + 2, bw + 2, 7)
            ui_rect(s, UI_ORO if i == 0 else (90, 150, 220), x + 215, yy + 3, bw, 5)
            s.blit(ui_texto(f"{v:.2f}".rstrip("0").rstrip("."), UI_CREMA), (x + 220 + bw, yy))
        s.blit(ui_texto("El diagnóstico CIE-10 (HU-003) va primero: WSJF 3.0", UI_ORO), (x, y + len(WSJF) * 11 + 3))
        return len(WSJF) * 11 + 14

    # --- Capítulo 2: conflictos ----------------------------------------------
    def _paginas_conflicto(self, k):
        conf = CONFLICTOS_C2[k]
        a, b = CONFLICTS[k]["members"]
        lado = {a: "izq", b: "der", "yo": "izq"}
        pags = []
        for t in conf.get("intro", []):                         # se presentan antes del problema
            pags.append(dict(tipo="dialogo", quien=t[0], texto=t[1], lado=lado.get(t[0], "izq"),
                             emo=t[2] if len(t) > 2 else EMO_ANTES.get(t[0])))
        if conf.get("apagon"):
            pags.append(dict(tipo="apagon"))
        for t in conf["antes"]:
            pags.append(dict(tipo="dialogo", quien=t[0], texto=t[1], lado=lado.get(t[0], "izq"),
                             emo=t[2] if len(t) > 2 else EMO_ANTES.get(t[0])))
        crit = " · ".join(f"C{i + 1} {n} ({p}%)" for i, (n, p) in enumerate(conf["criterios"]))
        pags.append(dict(tipo="alternativas", conf=k, crit=crit))
        letra, nombre, notas, total, _ = conf["alternativas"][-1]
        pags.append(dict(tipo="tarjeta", titulo=f"GANADORA: {letra} · {total:.2f} (CONSENSO)",
                         fuente=f"{conf['tabla']}, sección 2.5", icono="ok",
                         lineas=[(nombre, UI_ORO), (conf["acuerdo"], UI_CREMA)]))
        for quien, texto in conf["despues"]:
            pags.append(dict(tipo="dialogo", quien=quien, texto=texto, lado=lado.get(quien, "izq"),
                             emo=EMO_DESPUES.get(quien)))
        if k == "c1":                                           # el BPMN es el proceso de rectificación (Figura 16)
            pags.append(dict(tipo="dialogo", quien="yo", emo="contento",
                             texto="Esa rectificación es un proceso con flujos de excepción. Así lo modelamos en BPMN."))
            pags.append(dict(tipo="abrir", clave="bpmn", abierto=False))
        return pags

    def _fin_conflicto(self, k):
        self.c_resolved[k] = True
        self.show_banner(CONFLICTS[k]["resolution"])
        self._revisar_fin_c2()

    # --- Capítulo 3: el hilo dorado --------------------------------------------
    def _paginas_inicio_hilo(self):
        return [
            dict(tipo="dialogo", quien="yasuri", emo="neutral", texto="Buenos días. Vengo a atenderme.", lado="der"),
            dict(tipo="dialogo", quien="mariajose", emo="neutral", texto="Buenos días. Dame tu DNI y abro tu historia."),
            dict(tipo="dialogo", quien="yasuri", emo="preocupado", texto="Ay, no... creo que perdí mi DNI.", lado="der"),
            dict(tipo="dialogo", quien="yo", emo="sorprendido", texto="¿Sin DNI? ¿Y ahora cómo la registramos?"),
            dict(tipo="dialogo", quien="mariajose", emo="molesto",
                 texto="Antes, sin DNI, la historia se quedaba sin abrir o se duplicaba en papel."),
            dict(tipo="dialogo", quien="mariajose", emo="preocupado",
                 texto="Sin DNI igual tengo que abrirle su historia clínica. ¿El sistema lo permite?"),
            dict(tipo="dialogo", quien="yo", emo="neutral",
                 texto="Sí. Sigamos el hilo de ese requerimiento por todo el expediente: son 4 puertas, una por artefacto."),
        ]

    def _fin_inicio_hilo(self):
        self.c3["inicio"] = True
        self.show_banner("Sigue el hilo dorado: sal al pasillo y busca la puerta 1")

    def _puerta_hilo_cerca(self):
        fx, fy = self.mx + 16, self.my + 28
        for i, (px, py) in enumerate(PUERTAS_HILO):
            if abs(fx - px) < 16 and abs(fy - py) < 14:
                return i
        return None

    def _abrir_puerta(self, i):
        if i > self.c3["puertas"]:
            self.show_banner(f"Sigue el hilo: primero abre la puerta {self.c3['puertas'] + 1}")
            return
        pags = [self._tarjeta_puerta(i)]
        if i == 1:
            pags.append(dict(tipo="abrir", clave="casosdeuso", abierto=False))
        elif i == 2:
            pags.append(dict(tipo="abrir", clave="clases", abierto=False))
        if i == self.c3["puertas"]:
            self.c3["puertas"] += 1
            if self.c3["puertas"] == len(PUERTAS_HILO):
                pags += [
                    dict(tipo="dialogo", quien="yasuri", emo="contento", lado="der",
                         texto="¡Ya tengo mi historia clínica, gracias!"),
                    dict(tipo="dialogo", quien="mariajose", emo="contento",
                         texto="Con el código temporal quedó registrada."),
                    dict(tipo="dialogo", quien="yo", emo="contento",
                         texto="Así con cualquier requisito: si uno cambia, sabemos exactamente qué más cambia."),
                    dict(tipo="tarjeta", titulo="¿Y SI EL PROFE ELIGE OTRO REQUISITO?", fuente="Tabla 38", icono="ok",
                         lineas=[("Una buena segunda opción es la nota de rectificación:", UI_GRIS),
                                 ("RF-005A / RF-005B → CU-004 → AtencionMedica y NotaRectificacion → filas F-06 a F-09.", UI_CREMA),
                                 ("Ten el PDF del informe abierto en otra ventana por si piden ver la fila real.", UI_ORO)])]
                self._abrir_modal(pags, self._fin_hilo)
                return
        self._abrir_modal(pags)

    def _fin_hilo(self):
        self.c3["fin"] = True
        self._logro(CAPITULOS[2]["logro"])
        self.show_banner("¡Misión cumplida! Sal del centro de salud para el cierre")

    def _tarjeta_puerta(self, i):
        if i == 0:
            return dict(tipo="tarjeta", titulo="PUERTA 1 · EL REQUISITO (SRS)", fuente="Tabla 5 (catálogo RF/RNF)", icono="puerta",
                        lineas=[("RF-001 · MUST HAVE · Fuente: personal de admisión", UI_ORO),
                                ("El sistema debe permitir crear la Historia Clínica Electrónica con el DNI del paciente, "
                                 "o con un código temporal si el paciente no tiene DNI.", UI_CREMA),
                                ("Criterio de aceptación: con DNI busca la historia: si existe la recupera y si no, la crea. "
                                 "Sin DNI genera un código temporal único.", UI_GRIS)])
        if i == 1:
            return dict(tipo="tarjeta", titulo="PUERTA 2 · EL CASO DE USO", fuente="Figura 2 y Tabla 18", icono="puerta",
                        lineas=[("Ese requisito se vuelve el CU-001 · Abrir / crear historia clínica. Actor: Sra. María José.", UI_ORO),
                                ("Flujo principal (6 pasos): ingresa el DNI, el sistema verifica si ya existe, si no existe se crea "
                                 "la historia, se valida, se asigna el número único de HCE y se guarda.", UI_CREMA),
                                ("A1: si ya existe, se recupera sin crear otra.  E-1: faltan datos obligatorios.  "
                                 "E-2: el paciente no tiene DNI.", UI_GRIS)])
        if i == 2:
            return dict(tipo="tarjeta", titulo="PUERTA 3 · LAS CLASES", fuente="Figura 7 y Tabla 32", icono="puerta",
                        lineas=[("En el diagrama de clases, RF-001 vive en 3 clases (Tabla 32):", UI_GRIS),
                                ("CL-001 Persona: datos personales.", UI_CREMA),
                                ("CL-002 Paciente: DNI o código temporal.", UI_CREMA),
                                ("CL-005 HistoriaClinica: número único de HCE.", UI_CREMA),
                                ("Si el paciente no tiene DNI, el código temporal vive en Paciente.", UI_VERDE)])
        return dict(tipo="tarjeta", titulo="PUERTA 4 · LA MATRIZ", fuente="Tabla 38", icono="puerta",
                    lineas=[("Todo se junta en la fila F-01 de la matriz Requisito–CU–Clase–Prueba:", UI_GRIS)],
                    dibujo=self._dibujo_matriz)

    def _dibujo_matriz(self, s, x, y, w):
        pruebas = "PR-001 PR-002 PR-003"
        cols = [("FILA", 30), ("REQ.", 44), ("CU", 44), ("CLASES", 88), ("PRUEBAS", w - 206)]
        fila = ["F-01", "RF-001", "CU-001", "CL-001,002,005", pruebas]
        cx = x
        for (titulo, cw), valor in zip(cols, fila):
            ui_rect(s, UI_LINEA, cx, y, cw, 30)
            ui_rect(s, UI_FONDO2, cx + 1, y + 1, cw - 2, 12)
            ui_rect(s, (34, 46, 80), cx + 1, y + 14, cw - 2, 15)
            s.blit(ui_texto(titulo, UI_ORO), (cx + 3, y + 2))
            s.blit(ui_texto(ui_cortar(valor, cw - 6), UI_CREMA), (cx + 3, y + 17))
            cx += cw
        brillo = (self.t // 15) % 2 == 0                       # PR-003 parpadea
        px = x + 206 + 3 + ui_ancho("PR-001 PR-002 ") + 1
        ui_rect(s, UI_ORO if brillo else UI_ORO_OSC, px - 1, y + 26, ui_ancho("PR-003") + 2, 1)
        yy = y + 38
        s.blit(ui_texto("PR-001: DNI nuevo → se crea la HCE con número único.", UI_GRIS), (x, yy))
        s.blit(ui_texto("PR-002: DNI existente → se recupera la HCE sin duplicar.", UI_GRIS), (x, yy + 10))
        s.blit(ui_texto("PR-003: sin DNI → se genera un código temporal único.", UI_ORO), (x, yy + 20))
        return 70

    def _paginas_cierre(self):
        return [dict(tipo="tarjeta", titulo="CIERRE", fuente="Paso a las preguntas (2.4)", icono="ok",
                     lineas=sum(([(nombre.upper(), UI_ORO), (texto, UI_CREMA)] for nombre, texto in CIERRE), [])),
                dict(tipo="fin")]

    # --- dibujo del mundo (salas con visitas, hilo dorado) ----------------------
    def draw_world(self):
        self._c23()
        w, cw = self.world, self.chars
        cw.fill((0, 0, 0, 0))
        if self.scene == "ext":
            w.blit(self.bg_ext, (0, 0))
            dibujar_buzon(cw, BUZON_X, GROUND + 1, self.t, self.buzon_nuevo)
            self._dibujar_jugador_lado(cw)
        elif self.scene == "map":
            cx, cy = self.cam_mapa()
            w.blit(self.plano, (0, 0), (cx, cy, W, H))
            if self.capitulo == 3 and self.c3["inicio"]:
                self._dibujar_hilo(w, cx, cy)
            lista = []
            for n in NPCS:
                nx, ny = self.map_pos(n["id"])
                dx, dy, voltear = self._pose(n)
                im = self.npc_front[n["id"]]
                if voltear:
                    im = pygame.transform.flip(im, True, False)
                lista.append((ny, n, im, nx - cx + dx, ny - cy, dy))
            lista.append((self.my, None, self.map_player[self.mdir][self.frame], self.mx - cx, self.my - cy, 0))
            for _, n, im, x, y, dy in sorted(lista, key=lambda e: e[0]):
                cw.blit(self._sombra_mapa, (int(x) + 9, int(y) + 29))
                cw.blit(im, (int(x), int(y) + dy))
            for _, n, im, x, y, dy in lista:
                if n is not None:
                    self._particulas(cw, n, x + 16, y + dy, 1)
        else:
            w.blit(self.salas[self.sala], (0, 0))
            for n in self._presentes(self.sala):
                sx = self._sala_x(n["id"])
                dx, dy, voltear = self._pose(n)
                if voltear is None:
                    voltear = self.px + SPRITE / 2 > sx + SPRITE / 2
                img = self.npc_sprites[n["id"]]
                if voltear:
                    img = pygame.transform.flip(img, True, False)
                x = sx + dx * 2
                self._shadow(cw, x + SPRITE // 2, GROUND + 1)
                cw.blit(img, (x, GROUND - FEET + dy * 2))
                self._particulas(cw, n, x + SPRITE // 2, GROUND - FEET + dy * 2, 2)
            self._dibujar_jugador_lado(cw)

    def _dibujar_hilo(self, w, cx, cy):
        pts = [INICIO_HILO] + PUERTAS_HILO
        hechas = self.c3["puertas"]
        for k in range(len(PUERTAS_HILO)):
            (x0, y0), (x1, y1) = pts[k], pts[k + 1]
            largo = max(1, int(math.hypot(x1 - x0, y1 - y0)))
            for d in range(0, largo, 2):
                if k > hechas:
                    break
                if k == hechas and (d // 6 + self.t // 4) % 2:   # el tramo que falta: rayitas que avanzan
                    continue
                px = x0 + (x1 - x0) * d / largo - cx
                py = y0 + (y1 - y0) * d / largo - cy
                ui_rect(w, (150, 100, 24), int(px), int(py) + 1, 2, 2)
                ui_rect(w, (255, 214, 64), int(px), int(py), 2, 2)
        for i, (px, py) in enumerate(PUERTAS_HILO):
            x, y = px - cx, py - cy
            if not (-20 < x < W + 20 and -40 < y < H + 20):
                continue
            abierta = i < hechas
            sigue = i == hechas
            if sigue:                                           # brillo que late
                r = 13 + int(math.sin(self.t * 0.12) * 2)
                halo = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(halo, (255, 214, 64, 70), (r, r), r)
                w.blit(halo, (x - r, y - 12 - r))
            marco = (150, 100, 24) if not abierta else (80, 90, 110)
            relleno = (255, 214, 64) if not abierta else (140, 150, 170)
            ui_rect(w, UI_LINEA, x - 8, y - 24, 16, 24)
            ui_rect(w, marco, x - 7, y - 23, 14, 23)
            ui_rect(w, relleno, x - 5, y - 21, 10, 21)
            ui_rect(w, UI_LINEA, x - 7, y - 1, 14, 1)
            if abierta:
                ui_rect(w, (60, 70, 90), x - 5, y - 21, 3, 21)
            t = ui_texto(str(i + 1), UI_LINEA, None)
            w.blit(t, (x - t.get_width() // 2 + 1, y - 18))

    # --- interfaz: panel de tareas, misión, globos y ventana modal ---------------
    def _ui_panel(self, s):
        self._c23()
        if self.capitulo == 1:
            return self._ui_panel_c1(s)
        if not self.panel_visible:
            return
        if self.capitulo == 2:
            titulo = "DECISIONES"
            filas = [(self.c2["modulos"], "Prioriza 2 de 5 módulos", "Sala de reuniones")]
            filas += [(self.c_resolved[k], f"Conflicto {i + 1}", SALAS[CONFLICTOS_C2[k]["sala"]]["name"])
                      for i, k in enumerate(CONFLICTS)]
        else:
            titulo = "SIGUE EL HILO"
            filas = [(self.c3["inicio"], "Habla con María José", "Admisión")]
            nombres = ["El requisito", "El caso de uso", "Las clases", "La matriz"]
            filas += [(self.c3["puertas"] > i, f"Puerta {i + 1}", nombres[i]) for i in range(4)]
        hechas = sum(1 for f in filas if f[0])
        w = 162
        x, y = W - w - 4, 28
        alto = 20 + 11 * len(filas) + 3
        ui_marco(s, x, y, w, alto)
        ui_rect(s, UI_FONDO2, x + 3, y + 3, w - 6, 13)
        ui_rect(s, UI_ORO_OSC, x + 3, y + 16, w - 6, 1)
        s.blit(ui_texto(titulo, UI_ORO), (x + 8, y + 3))
        num = ui_texto(f"{hechas}/{len(filas)}", UI_CREMA)
        s.blit(num, (x + w - 8 - num.get_width(), y + 3))
        siguiente = next((i for i, f in enumerate(filas) if not f[0]), None)
        for i, (ok, txt, donde) in enumerate(filas):
            yy = y + 20 + i * 11
            if ok:
                ui_icono(s, x + 6, yy, ICONO_OK, PAL_OK)
            else:
                ui_rect(s, UI_LINEA, x + 7, yy + 1, 7, 7)
                ui_rect(s, (62, 78, 116), x + 8, yy + 2, 5, 5)
            color = UI_GRIS if ok else (UI_ORO if i == siguiente else UI_CREMA)
            s.blit(ui_texto(txt, color), (x + 18, yy))
            s.blit(ui_texto(ui_cortar(donde, w - 26 - ui_ancho(txt) - 8), (110, 124, 160)), (x + 18 + ui_ancho(txt) + 6, yy))

    def _ui_mision(self, s):
        self._c23()
        if self.capitulo == 1 or self.buzon_nuevo:
            return self._ui_mision_c1(s)
        if self.banner_t > 0 or self.menu is not None or self.modal is not None:
            return
        if self.capitulo == 2:
            lin = [("CAPÍTULO 2", UI_ORO), ("Prioriza los módulos y", UI_CREMA), ("resuelve 3 conflictos", UI_CREMA),
                   (f"Llevas {self._progreso_c2()}/4", UI_GRIS)]
        elif not self.c3["fin"]:
            lin = [("CAPÍTULO 3", UI_ORO), ("Sigue el hilo del RF-001", UI_CREMA), ("Empieza en Admisión", UI_CREMA),
                   (f"Puertas {self.c3['puertas']}/4", UI_GRIS)]
        else:
            lin = [("¡JUEGO COMPLETADO!", UI_ORO), ("Gracias por jugar", UI_CREMA)]
        bw = max(ui_ancho(l) for l, _ in lin) + 16
        ui_marco(s, 4, 28, bw, 10 * len(lin) + 8)
        for i, (l, c) in enumerate(lin):
            s.blit(ui_texto(l, c), (12, 32 + 10 * i))

    def _ui_actores(self, s):
        if self.scene != "sala":
            cx, cy = self.cam_mapa()
            for n in NPCS:
                nx, ny = self.map_pos(n["id"])
                dx, dy, _ = self._pose(n)
                sx, top, feet = nx + 16 - cx + dx, ny - cy + dy, ny + 30 - cy
                if 0 <= sx <= W and 0 <= feet <= H:
                    self._ui_globo_stakeholder(s, n, sx, top, feet, True)
            for k, c in CONFLICTS.items():
                if self.c_alpha[k] > 0.3 and not self.c_resolved[k]:
                    ax, ay = self.map_pos(c["members"][0])
                    bx, by = self.map_pos(c["members"][1])
                    self._ui_rayo(s, (ax + bx) / 2 + 16 - cx, (ay + by) / 2 - 8 - cy + math.sin(self.t * 0.2) * 2)
            return
        cerca = self._cerca_en_sala()
        presentes = self._presentes(self.sala)
        for n in presentes:
            if n is not cerca and len(presentes) > 1:
                self.npc_alpha[n["id"]] = min(self.npc_alpha[n["id"]], 0.4)   # un solo globo a la vez
            sx = self._sala_x(n["id"])
            dx, dy, _ = self._pose(n)
            self._ui_globo_stakeholder(s, n, sx + dx * 2 + SPRITE / 2, GROUND - FEET + dy * 2, None, False)
        if self.capitulo == 2 and len(presentes) > 1:            # rayo entre los dos que discuten
            k = TAREA_DE_SALA.get(self.sala)
            if k in CONFLICTS and not self.c_resolved[k]:
                xs = [self._sala_x(n["id"]) + SPRITE / 2 for n in presentes]
                self._ui_rayo(s, sum(xs) / len(xs), GROUND - FEET - 4 + math.sin(self.t * 0.2) * 2)

    def _retrato(self, quien, emo=None):
        """Retrato 60x60 para los diálogos. Busca assets/retrato_<personaje>_<emocion>.png;
        si falta, prueba con una emoción parecida, luego con la neutral y al final con el muñequito."""
        clave = (quien, emo)
        if clave in self._retratos:
            return self._retratos[clave]
        pid = "jugador" if quien == "yo" else quien
        pruebas = []
        if emo:
            pruebas += [emo] + EMO_PARECIDAS.get(emo, [])
        pruebas += ["neutral", None]
        im = None
        for e in pruebas:
            p = res(f"assets/retrato_{pid}_{e}.png" if e else f"assets/retrato_{pid}.png")
            if os.path.exists(p):
                big = pygame.image.load(p).convert_alpha()
                im = pygame.transform.smoothscale(big, (60, 60))
                break
        if im is None:
            base = self.map_player["frente"][0] if quien == "yo" else self.npc_front[quien]
            im = pygame.transform.scale(base.subsurface((6, 0, 20, 20)).copy(), (60, 60))
        self._retratos[clave] = im
        return im

    def _ui_modal(self, s):
        m = self.modal
        if m is None:
            return
        p = m["paginas"][m["i"]]
        tipo = p["tipo"]
        if tipo == "dialogo":
            self._ui_dialogo(s, p, m)
        elif tipo == "apagon":
            self._ui_apagon(s, m)
        elif tipo == "fin":
            self._ui_fin(s, m)
        elif tipo == "abrir":
            self._ui_abrir(s, p, m)
        else:
            ui_rect(s, (0, 0, 0, 150), 0, 0, W, H)
            x, y, w, h = 18, 26, W - 36, H - 32
            ui_marco(s, x, y, w, h)
            ui_rect(s, UI_FONDO2, x + 3, y + 3, w - 6, 13)
            ui_rect(s, UI_ORO_OSC, x + 3, y + 16, w - 6, 1)
            tx = x + 8
            if p.get("icono") == "puerta":
                ui_rect(s, UI_LINEA, tx, y + 4, 8, 11)
                ui_rect(s, (255, 214, 64), tx + 1, y + 5, 6, 10)
                tx += 12
            elif p.get("icono") == "ok":
                ui_icono(s, tx, y + 5, ICONO_OK, PAL_OK)
                tx += 13
            if tipo == "modulos":
                titulo = "PRESUPUESTO: SOLO 2 DE 5 MÓDULOS"
            elif tipo == "alternativas":
                titulo = CONFLICTOS_C2[p["conf"]]["titulo"]
            else:
                titulo = p["titulo"]
            s.blit(ui_texto(titulo, UI_ORO), (tx, y + 4))
            cuerpo_y = y + 21
            if tipo == "tarjeta":
                yy = cuerpo_y
                for texto, color in p.get("lineas", []):
                    for l in ui_partir(texto, w - 18):
                        s.blit(ui_texto(l, color), (x + 9, yy))
                        yy += 10
                    yy += 3
                if p.get("dibujo"):
                    p["dibujo"](s, x + 9, yy + 2, w - 18)
                pie = "CONTINUAR"
            elif tipo == "modulos":
                self._ui_modulos(s, m, x, cuerpo_y, w)
                pie = "CONTINUAR" if len(m["elegidos"]) >= 2 else "PONER MONEDA"
            else:
                self._ui_alternativas(s, m, p, x, cuerpo_y, w)
                pie = "ELEGIR"
            # pie: fuente del informe + teclas
            fy = y + h - 16
            ui_rect(s, (62, 78, 116), x + 6, fy - 3, w - 12, 1)
            if p.get("fuente"):
                s.blit(ui_texto("VER: " + p["fuente"], (110, 124, 160)), (x + 9, fy + 1))
            hx = x + w - 10 - ui_ancho(pie) - 18
            if tipo in ("modulos", "alternativas"):
                hx -= 34
                kx = hx
                for k in ("W", "S"):
                    kx += ui_tecla(s, kx, fy - 1, k) + 2
                hx = kx + 6
            if m["t"] > 8 or tipo != "tarjeta":
                ui_tecla(s, hx, fy - 1, "E", (self.t // 24) % 2 == 1)
                s.blit(ui_texto(pie, UI_CREMA), (hx + 13, fy + 1))

    def _ui_abrir(self, s, p, m):
        """Aviso: ¿quieres abrir el diagrama? (SÍ lo abre desde la carpeta diagramas)."""
        ui_rect(s, (0, 0, 0, 150), 0, 0, W, H)
        bw, bh = 290, 118
        x, y = (W - bw) // 2, (H - bh) // 2
        ui_marco(s, x, y, bw, bh)
        ui_rect(s, UI_FONDO2, x + 3, y + 3, bw - 6, 13)
        ui_rect(s, UI_ORO_OSC, x + 3, y + 16, bw - 6, 1)
        s.blit(ui_texto("ABRIR DIAGRAMA", UI_ORO), (x + 9, y + 4))
        yy = y + 22
        for l in ui_partir("¿QUIERES ABRIR " + DIAGRAMAS[p["clave"]][0] + "?", bw - 18):
            s.blit(ui_texto(l, UI_CREMA), (x + 9, yy))
            yy += 10
        if m["msg"]:
            texto, color = m["msg"]
            for l in ui_partir(texto, bw - 18)[:4]:
                s.blit(ui_texto(l, color), (x + 9, yy + 3))
                yy += 10
        if p.get("abierto"):
            ui_tecla(s, x + bw - 78, y + bh - 17, "E", (self.t // 24) % 2 == 1)
            s.blit(ui_texto("CONTINUAR", UI_CREMA), (x + bw - 65, y + bh - 15))
            return
        for k, txt in enumerate(("SÍ, ABRIRLO", "NO, SEGUIR")):
            sel = (m["sel"] == k)
            ox, oy = x + 20 + k * 136, y + bh - 31
            ui_marco(s, ox, oy, 114, 16, borde=UI_ORO if sel else (62, 78, 116),
                     fondo=UI_FONDO2 if sel else UI_FONDO, brillo=sel)
            t = ui_texto(txt, UI_CREMA if sel else UI_GRIS)
            s.blit(t, (ox + (114 - t.get_width()) // 2, oy + 4))
        h = ui_texto("A D ELEGIR · E ACEPTAR", (110, 124, 160))
        s.blit(h, (x + (bw - h.get_width()) // 2, y + bh - 12))

    def _ui_dialogo(self, s, p, m):
        quien = p["quien"]
        if quien == "yo":
            nombre, rol = "Tú", "Equipo de ingeniería"
        else:
            n = self.npc_by_id[quien]
            nombre, rol = n["name"], n["role"]
        der = p.get("lado") == "der"
        x, y, w, h = 6, H - 72, W - 12, 66
        ui_rect(s, (0, 0, 0, 70), 0, 0, W, H)
        ui_marco(s, x, y, w, h)
        rx = x + w - 66 if der else x + 6
        ui_rect(s, UI_LINEA, rx - 1, y + 2, 62, 62)
        ui_rect(s, (58, 74, 118), rx, y + 3, 60, 60)
        ui_rect(s, (72, 92, 146), rx, y + 3, 60, 20)
        s.blit(self._retrato(quien, p.get("emo")), (rx, y + 3))
        # cartelito con el nombre
        nt = nombre.upper() + "  ·  " + rol
        nw = ui_ancho(nt) + 14
        nx = (x + w - nw - 70) if der else (x + 70)
        ui_marco(s, nx, y - 12, nw, 15)
        s.blit(ui_texto(nombre, UI_ORO), (nx + 7, y - 9))
        s.blit(ui_texto("  ·  " + rol, UI_GRIS), (nx + 7 + ui_ancho(nombre), y - 9))
        # texto que se escribe solo
        tx = x + 8 if der else x + 74
        quedan = int(m["t"] * TEXTO_VEL)
        for i, l in enumerate(self._texto_dialogo(p)):
            if quedan <= 0:
                break
            s.blit(ui_texto(l[:quedan], UI_CREMA), (tx, y + 9 + i * 11))
            quedan -= len(l)
        if quedan > 0 and (self.t // 20) % 2 == 0:               # flechita para continuar
            ax, ay = (x + w - 82 if der else x + w - 14), y + h - 10
            for k in range(4):
                ui_rect(s, UI_ORO, ax - 3 + k, ay + k, 7 - 2 * k, 1)

    def _ui_modulos(self, s, m, x, y, w):
        for k in range(2):                                      # las 2 monedas
            cx = x + w - 30 + k * 12
            usada = k < len(m["elegidos"])
            pygame.draw.circle(s, UI_LINEA, (cx, y - 13), 5)
            pygame.draw.circle(s, (110, 110, 120) if usada else (255, 200, 60), (cx, y - 13), 4)
            if not usada:
                ui_rect(s, (255, 240, 170), cx - 2, y - 15, 1, 2)
        for i, mod in enumerate(MODULOS):
            ry = y + 2 + i * 20
            elegido, bloq, sel = i in m["elegidos"], i in m["bloq"], i == m["sel"]
            fondo = (48, 64, 106) if sel else (28, 38, 66)
            ui_rect(s, fondo, x + 8, ry, w - 16, 18)
            if sel:
                for (rx, ry2, rw, rh) in ((x + 8, ry, w - 16, 1), (x + 8, ry + 17, w - 16, 1), (x + 8, ry, 1, 18), (x + w - 9, ry, 1, 18)):
                    ui_rect(s, UI_ORO, rx, ry2, rw, rh)
            s.blit(ui_texto(mod["nombre"], UI_GRIS if bloq else UI_CREMA), (x + 26, ry + 5))
            if elegido:
                pygame.draw.circle(s, UI_LINEA, (x + 17, ry + 9), 5)
                pygame.draw.circle(s, (255, 200, 60), (x + 17, ry + 9), 4)
                tag, col = mod["moscow"], UI_VERDE
            elif bloq:
                tag, col = "FASE 2 · " + mod["moscow"], UI_ROJO
                ui_rect(s, UI_ROJO, x + 24, ry + 9, ui_ancho(mod["nombre"]) + 4, 1)
            else:
                tag, col = "", UI_GRIS
            if tag:
                s.blit(ui_texto(tag, col), (x + w - 14 - ui_ancho(tag), ry + 5))
        if m["msg"]:
            texto, color = m["msg"]
            for k, l in enumerate(ui_partir(texto, w - 18)[:2]):
                s.blit(ui_texto(l, color), (x + 9, y + 104 + k * 10))

    def _ui_alternativas(self, s, m, p, x, y, w):
        conf = CONFLICTOS_C2[p["conf"]]
        for k, l in enumerate(ui_partir(p["crit"], w - 18)[:2]):
            s.blit(ui_texto(l, UI_GRIS), (x + 9, y + k * 10))
        ty = y + 24
        nombre_w = w - 16 - 4 * 20 - 34
        cabe = ["ALTERNATIVA"] + [f"C{i + 1}" for i in range(4)] + ["TOTAL"]
        cx = x + 8
        for i, c in enumerate(cabe):
            cw = nombre_w if i == 0 else (20 if i < 5 else 34)
            s.blit(ui_texto(c, UI_ORO), (cx + 3, ty))
            cx += cw
        for r, (letra, nombre, notas, total, motivo) in enumerate(conf["alternativas"]):
            ry = ty + 12 + r * 20
            sel, tach = r == m["sel"], r in m["tachadas"]
            ui_rect(s, (48, 64, 106) if sel else (28, 38, 66), x + 8, ry, w - 16, 18)
            if sel:
                for (rx, ry2, rw, rh) in ((x + 8, ry, w - 16, 1), (x + 8, ry + 17, w - 16, 1), (x + 8, ry, 1, 18), (x + w - 9, ry, 1, 18)):
                    ui_rect(s, UI_ORO, rx, ry2, rw, rh)
            col = UI_GRIS if tach else UI_CREMA
            lin = ui_partir(f"{letra}. {nombre}", nombre_w - 8)[:2]
            for j, l in enumerate(lin):
                s.blit(ui_texto(l, col), (x + 11 + (0 if j == 0 else 12), ry + (5 if len(lin) == 1 else 1 + 9 * j)))
            cx = x + 8 + nombre_w
            for v in notas:
                s.blit(ui_texto(str(v), col), (cx + 6, ry + 5))
                cx += 20
            s.blit(ui_texto(f"{total:.2f}", UI_ORO if not tach else UI_GRIS), (cx + 5, ry + 5))
            if tach:
                ui_rect(s, UI_ROJO, x + 10, ry + 9, w - 20, 1)
        if m["msg"]:
            texto, color = m["msg"]
            for k, l in enumerate(ui_partir(texto, w - 18)[:2]):
                s.blit(ui_texto(l, color), (x + 9, ty + 76 + k * 10))
        else:
            s.blit(ui_texto("¿Cuál camino eligió el equipo por consenso?", UI_GRIS), (x + 9, ty + 76))

    def _ui_apagon(self, s, m):
        t = m["t"]
        parpadeo = t < 40 and (t // 4) % 3 == 0
        ui_rect(s, (0, 0, 0, 120 if parpadeo else 215), 0, 0, W, H)
        if t > 20:
            t1 = ui_texto("¡SE CORTÓ LA CONEXIÓN!", (255, 214, 64))
            s.blit(t1, (W // 2 - t1.get_width() // 2, H // 2 - 14))
            t2 = ui_texto("Sara estaba registrando los signos vitales...", UI_CREMA)
            s.blit(t2, (W // 2 - t2.get_width() // 2, H // 2))
            ui_icono(s, W // 2 - 4, H // 2 - 34, ICONO_RAYO, PAL_RAYO)

    def _ui_fin(self, s, m):
        ui_rect(s, (8, 12, 24, 235), 0, 0, W, H)
        for k in range(18):                                     # estrellitas
            sx = (k * 97 + self.t // 3) % W
            sy = (k * 53) % H
            ui_rect(s, (255, 214, 64) if (k + self.t // 10) % 3 else UI_CREMA, sx, sy, 1, 1)
        lineas = [("FIN", (255, 214, 64)), ("", None), ("¡Gracias!", UI_CREMA),
                  ("Estamos listos para sus preguntas", UI_CREMA), ("", None),
                  ("DIRESA La Libertad · Ingeniería de Software CIIN1252P", UI_GRIS), (CREDITOS, UI_ORO)]
        yy = 50
        for texto, color in lineas:
            if texto:
                t = ui_texto(texto, color)
                if texto == "FIN":
                    t = pygame.transform.scale(t, (t.get_width() * 3, t.get_height() * 3))
                s.blit(t, (W // 2 - t.get_width() // 2, yy))
                yy += t.get_height() + 2
            else:
                yy += 8
        if m["t"] > 30 and (self.t // 24) % 2 == 0:
            t = ui_texto("Presiona E para volver al juego", UI_GRIS)
            s.blit(t, (W // 2 - t.get_width() // 2, H - 22))

    def draw_ui(self, screen):
        self._ui_init()
        self._c23()
        s = self.ui
        s.fill((0, 0, 0, 0))
        quien = None
        pregunta = None
        libre = self.trans is None and self.menu is None and self.modal is None
        if self.scene == "ext":
            zona = "Exterior · Centro de salud"
            if libre and self.near_door():
                pregunta = "ENTRAR"
            elif libre and self.cerca_buzon():
                pregunta = "VER CAPÍTULOS"
        elif self.scene == "map":
            cx, cy = self.cam_mapa()
            zona = "Centro de salud"
            quien = (self.mx + 16 - cx, self.my - cy)
            puerta = self._puerta_hilo_cerca() if (self.capitulo == 3 and self.c3["inicio"]) else None
            if libre and puerta is not None:
                pregunta = f"ABRIR LA PUERTA {puerta + 1}"
            elif libre and not self.lock_door and self._puerta_actual():
                pregunta = "ENTRAR"
            elif libre and self.en_salida():
                pregunta = "SALIR"
        else:
            zona = SALAS[self.sala]["name"]
            quien = (self.px + SPRITE / 2, GROUND - FEET)
            tarea = self._tarea_sala() if libre else None
            if tarea == "modulos":
                pregunta = "DECIDIR LOS MÓDULOS"
            elif tarea in CONFLICTS:
                pregunta = "RESOLVER EL CONFLICTO"
            elif tarea == "hilo":
                pregunta = "HABLAR"
            elif libre and self.px < 34:
                pregunta = "SALIR"

        self._ui_barra(s, zona)
        if self.modal is None:
            if self.scene == "ext":
                self._ui_mision(s)
            else:
                self._ui_panel(s)
            self._ui_actores(s)
            self._ui_aviso(s)
            if pregunta:
                if quien:
                    self._ui_tecla_flotante(s, quien[0], quien[1])
                self._ui_prompt(s, "PRESIONE", "E", "PARA " + pregunta)
            if self.menu is None:
                self._ui_ayuda(s, self.scene == "map")
        self._ui_modal(s)
        self._ui_logro(s)
        self._ui_menu(s)
        screen.blit(pygame.transform.scale(s, (SCREEN_W, SCREEN_H)), (0, 0))
    # ======================== FIN DE LOS CAPÍTULOS 2 Y 3 ========================

    # ======================================================================
    # PANTALLA DE INICIO + CINEMÁTICA (el juego arranca en "titulo", luego "cine", luego "juego")
    # ======================================================================
    fase = "juego"                 # main() la pone en "titulo"; las pruebas arrancan directo en "juego"
    _render_c23 = render
    _update_c23 = update
    _tecla_c23 = tecla
    _elegir_capitulo_c23 = _elegir_capitulo

    def iniciar_con_menu(self):
        self.fase = "titulo"
        self._ini_init()

    def _ini_init(self):
        if hasattr(self, "_ti_s"):
            return
        self._ui_init()
        self._c23()
        self._ti_s = pygame.Surface((W, H))
        self._ti_fondo = crear_fondo_ciudad()
        self._ti_sel = 0
        self._ti_t = 0
        self._ti_mouse = None
        self._fade_in = 0
        self._ti_tapa = pygame.Surface((W, H), pygame.SRCALPHA)
        p = res("assets/npc_pacientes2_izquierda.png")
        base = pygame.image.load(p).convert_alpha() if os.path.exists(p) else make_npc_sprite((120, 150, 190), (240, 200, 90), "paciente")
        self._cine_img = dict(self.npc_sprites)
        self._cine_img["pacientes2"] = grow(base)
        self.cine = dict(i=0, t=0, estado="in", e=0, destino=0)
        self._tit_grande = _texto_grande(TITULO_TXT, 7, UI_ORO, claro=(255, 226, 120))
        self._tit_sub = _texto_grande(SUBTITULO_TXT, 3, UI_CREMA, claro=(255, 255, 255))

    # --- teclas y mouse -----------------------------------------------------
    def tecla(self, key):
        if key == pygame.K_m:                                   # silenciar / activar las voces
            if not hasattr(self, "_voz"):
                self._voz = Voces()
            self._voz.activo = not self._voz.activo
            self.show_banner("Sonido: " + ("ACTIVADO" if self._voz.activo else "SILENCIADO"))
            return None
        if self.fase == "titulo":
            self._ini_init()
            if key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                self._ti_sel = 1 - self._ti_sel
            elif key in (pygame.K_e, pygame.K_RETURN, pygame.K_SPACE):
                return self._elegir_inicio(self._ti_sel)
            elif key == pygame.K_ESCAPE:
                return "salir"
            return None
        if self.fase == "tarjeta_cap":
            if key in (pygame.K_e, pygame.K_RETURN, pygame.K_SPACE) and 44 < self._cap["t"] < 150:
                self._cap["t"] = 150                           # adelanta hasta que se desvanezca
            return None
        if self.fase == "cine":
            if key in (pygame.K_e, pygame.K_RETURN, pygame.K_SPACE, pygame.K_RIGHT, pygame.K_d):
                self._cine_mover(+1)
            elif key in (pygame.K_a, pygame.K_LEFT):
                self._cine_mover(-1)
            elif key == pygame.K_ESCAPE:
                self._cine_saltar()
            return None
        return self._tecla_c23(key)

    def clic(self, pos):
        """Clic del mouse (pos en píxeles de la ventana de 1152x648)."""
        if self.fase == "titulo":
            self._ini_init()
            mx, my = pos[0] / SCALE, pos[1] / SCALE
            for i in range(2):
                if BTN_X <= mx <= BTN_X + BTN_W and BTN_Y[i] <= my <= BTN_Y[i] + BTN_H:
                    self._ti_sel = i
                    return self._elegir_inicio(i)
        elif self.fase == "cine":
            self._cine_mover(+1)
        return None

    def _elegir_inicio(self, i):
        if i == 1:
            return "salir"
        self.fase = "cine"
        self.cine = dict(i=0, t=0, estado="in", e=0, destino=0)
        return None

    # --- cinemática: avanzar / retroceder -----------------------------------------
    def _cine_mover(self, d):
        c = self.cine
        if c["estado"] != "play":
            return
        destino = c["i"] + d
        if destino < 0:
            return
        c["estado"], c["e"], c["destino"] = "out", 0, destino

    def _cine_saltar(self):
        c = self.cine
        if c["estado"] == "play" or c["estado"] == "in":
            c["estado"], c["e"], c["destino"] = "out", 0, len(CINE_ESCENAS) + 1

    def _elegir_capitulo(self):
        """Desde el buzón: sale la pantalla negra 'CAPÍTULO N + título' y recién ahí cambia el capítulo."""
        self._ini_init()
        self._cap = dict(sel=self.menu["sel"], t=0, hecho=False)
        self.menu = None
        self.fase = "tarjeta_cap"

    def _empezar_juego(self):
        self.fase = "juego"
        self._fade_in = 50

    # --- actualizar -----------------------------------------------------------
    def update(self, left, right, up=False, down=False, run=False):
        if self.fase == "juego":
            if getattr(self, "_fade_in", 0) > 0:
                self._fade_in -= 1
            return self._update_c23(left, right, up, down, run)
        self._ini_init()
        self.t += 1
        self._ti_t += 1
        if self.fase == "tarjeta_cap":
            c = self._cap
            c["t"] += 1
            if c["t"] >= 26 and not c["hecho"]:                 # ya está todo negro: cambia el capítulo
                c["hecho"] = True
                self.menu = dict(sel=c["sel"])
                self._elegir_capitulo_c23()
            if c["t"] >= 200:
                self.fase = "juego"
            return
        if self.fase == "cine":
            c = self.cine
            c["t"] += 1
            c["e"] += 1 if c["estado"] != "play" else 0
            if c["estado"] == "in" and c["e"] >= 16:
                c["estado"] = "play"
            elif c["estado"] == "out" and c["e"] >= 16:
                if c["destino"] > len(CINE_ESCENAS):
                    self._empezar_juego()
                else:
                    c["i"], c["t"], c["estado"], c["e"] = c["destino"], 0, "in", 0
            elif c["estado"] == "play" and c["i"] == len(CINE_ESCENAS) and c["t"] > 220:
                self._cine_mover(+1)

    # --- dibujar --------------------------------------------------------------
    def render(self, screen):
        if self.fase == "juego":
            self._render_c23(screen)
            if getattr(self, "_fade_in", 0) > 0:
                self._fade_surf.set_alpha(int(255 * self._fade_in / 50))
                screen.blit(self._fade_surf, (0, 0))
            return
        self._ini_init()
        if self.fase == "tarjeta_cap":
            self._render_c23(screen)
            self._dibujar_tarjeta_cap(screen)
            return
        s = self._ti_s
        if self.fase == "titulo":
            self._dibujar_titulo(s)
        else:
            self._dibujar_cine(s)
        pygame.transform.scale(s, (SCREEN_W, SCREEN_H), screen)

    def _pintar_cap(self, s, linea1, linea2, alfa=255):
        """Texto del capítulo: 'CAPÍTULO N' grande en dorado y el título abajo."""
        a = _texto_grande(linea1, 3, UI_ORO, claro=(255, 226, 120))
        b = ui_texto(linea2, UI_CREMA)
        b = pygame.transform.scale(b, (b.get_width() * 2, b.get_height() * 2))
        for img, y in ((a, 78), (b, 118)):
            img = img.copy()
            img.set_alpha(int(alfa))
            s.blit(img, ((W - img.get_width()) // 2, y))

    def _dibujar_tarjeta_cap(self, screen):
        c = self._cap
        t = c["t"]
        if t < 24:
            fondo = 255 * t / 24
        elif t < 170:
            fondo = 255
        else:
            fondo = 255 * max(0.0, 1 - (t - 170) / 30)
        if t < 24:
            txt = 0
        elif t < 44:
            txt = 255 * (t - 24) / 20
        elif t < 150:
            txt = 255
        else:
            txt = 255 * max(0.0, 1 - (t - 150) / 20)
        tapa = self._ti_tapa
        tapa.fill((0, 0, 0, int(fondo)))
        if txt > 0:
            self._pintar_cap(tapa, f"CAPÍTULO {c['sel'] + 1}", CAPITULOS[c["sel"]]["titulo"], txt)
        screen.blit(pygame.transform.scale(tapa, (SCREEN_W, SCREEN_H)), (0, 0))

    def _dibujar_titulo(self, s):
        f, t = self._ti_fondo, self._ti_t
        # mouse: si lo mueves encima de un botón, lo selecciona
        mp = pygame.mouse.get_pos() if pygame.mouse.get_focused() else None
        if mp is not None and mp != self._ti_mouse:
            mx, my = mp[0] / SCALE, mp[1] / SCALE
            for i in range(2):
                if BTN_X <= mx <= BTN_X + BTN_W and BTN_Y[i] <= my <= BTN_Y[i] + BTN_H:
                    self._ti_sel = i
        self._ti_mouse = mp
        s.blit(f["cielo"], (0, 0))
        for (x, y, fase) in f["estrellas"]:
            b = math.sin(t * 0.04 + fase)
            col = (255, 255, 255) if b > 0.2 else ((170, 176, 220) if b > -0.5 else (96, 100, 150))
            s.set_at((x, y), col)
            if b > 0.8:
                s.set_at((x + 1, y), col)
                s.set_at((x, y + 1), col)
        # nubes que pasan despacio
        for k, (cy, vel, ancho) in enumerate(((58, 0.10, 34), (86, 0.07, 46), (40, 0.05, 28))):
            cx = int((k * 150 + t * vel) % (W + 80)) - 40
            col = (120, 84, 150) if k != 2 else (70, 60, 120)
            pygame.draw.rect(s, col, (cx, cy, ancho, 5))
            pygame.draw.rect(s, col, (cx + 6, cy - 4, ancho - 14, 5))
        s.blit(f["lejos"], (-int(t * 0.10) % W - W, 0))
        s.blit(f["lejos"], (-int(t * 0.10) % W, 0))
        s.blit(f["medio"], (-int(t * 0.25) % W - W, 0))
        s.blit(f["medio"], (-int(t * 0.25) % W, 0))
        s.blit(f["cerca"], (0, 0))
        # postes de luz
        for px in f["postes"]:
            pygame.draw.rect(s, UI_LINEA, (px, 160, 2, 30))
            pygame.draw.rect(s, UI_LINEA, (px - 3, 158, 8, 3))
            on = 1 if (t // 90 + px) % 23 else 0.8
            pygame.draw.rect(s, (255, 232, 150), (px - 2, 161, 6, 2))
            halo = pygame.Surface((26, 18), pygame.SRCALPHA)
            pygame.draw.ellipse(halo, (255, 220, 130, int(34 * on)), (0, 0, 26, 18))
            s.blit(halo, (px - 12, 158))
        # el carrito que cruza la calle
        cx = int((t * 0.9) % (W + 260)) - 60
        pygame.draw.rect(s, UI_LINEA, (cx - 1, 197, 24, 9))
        pygame.draw.rect(s, (204, 62, 70), (cx, 199, 22, 6))
        pygame.draw.rect(s, (204, 62, 70), (cx + 5, 196, 11, 4))
        pygame.draw.rect(s, (170, 220, 245), (cx + 6, 197, 9, 3))
        pygame.draw.rect(s, UI_LINEA, (cx + 3, 204, 4, 3))
        pygame.draw.rect(s, UI_LINEA, (cx + 15, 204, 4, 3))
        pygame.draw.rect(s, (255, 240, 170), (cx + 22, 200, 2, 2))
        haz = pygame.Surface((22, 8), pygame.SRCALPHA)
        pygame.draw.polygon(haz, (255, 240, 170, 60), [(0, 3), (22, 0), (22, 8)])
        s.blit(haz, (cx + 23, 198))
        # título
        tit = self._tit_grande
        s.blit(tit, ((W - tit.get_width()) // 2, 12 + int(math.sin(t * 0.045) * 2)))
        sub = self._tit_sub
        yy = 12 + tit.get_height() + 3
        for lado in (-1, 1):                                    # rayitas a los lados del subtítulo
            lx = W // 2 + lado * (sub.get_width() // 2 + 8)
            pygame.draw.rect(s, UI_ORO_OSC, (lx if lado > 0 else lx - 36, yy + sub.get_height() // 2 - 1, 36, 2))
            pygame.draw.rect(s, UI_ORO, (lx if lado > 0 else lx - 36, yy + sub.get_height() // 2 - 2, 36, 1))
        s.blit(sub, ((W - sub.get_width()) // 2, yy))
        # botones
        for i, nombre in enumerate(BOTONES_INICIO):
            sel = (i == self._ti_sel)
            y = BTN_Y[i] + (1 if sel and (t // 20) % 2 else 0)
            ui_marco(s, BTN_X, y, BTN_W, BTN_H, borde=UI_ORO if sel else (62, 78, 116),
                     fondo=UI_FONDO2 if sel else UI_FONDO, brillo=sel)
            tx = ui_texto(nombre, UI_CREMA if sel else UI_GRIS)
            s.blit(tx, (BTN_X + (BTN_W - tx.get_width()) // 2, y + 4))
            if sel:
                fl = 2 if (t // 16) % 2 else 0
                for lado in (0, 1):
                    ax = BTN_X + 8 - fl if lado == 0 else BTN_X + BTN_W - 12 + fl
                    pts = [(ax, y + 4), (ax, y + 12), (ax + 4, y + 8)] if lado == 0 else [(ax + 4, y + 4), (ax + 4, y + 12), (ax, y + 8)]
                    pygame.draw.polygon(s, UI_ORO, pts)
        pie = ui_texto("ACORI Y. · CANDIOTTI M. · GAITAN G.", UI_CREMA)
        s.blit(pie, ((W - pie.get_width()) // 2, 184))
        pie2 = ui_texto("CIIN1252P · INGENIERÍA DE SOFTWARE", UI_GRIS)
        s.blit(pie2, (6, H - 12))
        pie3 = ui_texto("W S · E ELEGIR", UI_GRIS)
        s.blit(pie3, (W - pie3.get_width() - 6, H - 12))

    # --- cinemática ---------------------------------------------------------
    def _c_npc(self, s, key, x, dy=0, flip=False):
        img = self._cine_img[key]
        if flip:
            img = pygame.transform.flip(img, True, False)
        self._shadow(s, x + SPRITE // 2, GROUND + 1)
        s.blit(img, (int(x), GROUND - FEET + int(dy)))

    def _dibujar_cine(self, s):
        c = self.cine
        i, t = c["i"], c["t"]
        if i < len(CINE_ESCENAS):
            getattr(self, "_cine_" + CINE_ESCENAS[i])(s, t)
            # puntitos de avance + ayuda
            n = len(CINE_ESCENAS)
            x0 = 6
            for k in range(n):
                col = UI_ORO if k == i else (62, 78, 116)
                pygame.draw.rect(s, UI_LINEA, (x0 + k * 8 - 1, H - 10, 7, 7))
                pygame.draw.rect(s, col, (x0 + k * 8, H - 9, 5, 5))
            ayu = ui_texto("E SIGUIENTE · ESC SALTAR", UI_GRIS)
            s.blit(ayu, (W - ayu.get_width() - 5, H - 11))
        else:
            s.fill((0, 0, 0))
            self._pintar_cap(s, CAPITULO1_TARJETA[0], CAPITULO1_TARJETA[1])
        al = 0
        if c["estado"] == "in":
            al = 255 * (1 - c["e"] / 16)
        elif c["estado"] == "out":
            al = 255 * min(1, c["e"] / 16)
        if al > 0:
            self._ti_tapa.fill((0, 0, 0, int(al)))
            s.blit(self._ti_tapa, (0, 0))

    def _cine_escena1_fondo(self, s, sala):
        s.blit(self.salas[sala], (0, 0))

    # Escena 1: Admisión. Todo a mano, los papeles se amontonan y los pacientes esperan.
    def _cine_admision(self, s, t):
        s.blit(self.salas["admision"], (0, 0))
        ciclo = t % 1000
        n = min(15, ciclo // 50)
        rnd = random.Random(5)
        for k in range(n):                                       # montón de hojas sobre el mostrador
            jx = rnd.randrange(-4, 5)
            col = (250, 250, 246) if k % 2 else (236, 240, 248)
            pygame.draw.rect(s, UI_LINEA, (213 + jx, 141 - k * 2 - 1, 24, 4))
            pygame.draw.rect(s, col, (213 + jx + 1, 141 - k * 2, 22, 2))
        if n >= 11:                                              # se cae una hoja de vez en cuando
            for q in range(2):
                p = (t + q * 45) % 90
                _c_hoja(s, 236 + int(math.sin(p * 0.12 + q) * 7) + p // 6, 118 + p * 0.78, 8, 10)
        mj = self.npc_by_id["mariajose"]
        self._c_npc(s, "mariajose", 108, -((t // 9) % 2), flip=True)
        self._particulas(s, mj, 108 + SPRITE // 2, GROUND - FEET, 2)
        # escribiendo a mano en su cuaderno
        _c_cuaderno(s, 138, 166, 22, 15)
        lx = 150 + int(math.sin(t * 0.5) * 4)
        pygame.draw.line(s, UI_LINEA, (lx, 166), (lx - 5, 158), 3)
        pygame.draw.line(s, (240, 200, 60), (lx, 166), (lx - 5, 158), 1)
        if 110 < t % 260 < 230:
            _c_globo(s, 108 + SPRITE // 2 + 4, GROUND - FEET - 17, "?", (200, 60, 70))
        # los pacientes esperando
        _ = self._c_npc(s, "yasuri", 288, -((t // 28) % 2), flip=False)
        self._c_npc(s, "pacientes2", 330, -(((t + 14) // 28) % 2), flip=False)
        if (t // 100) % 2:
            _c_globo(s, 288 + SPRITE // 2, GROUND - FEET - 17, "", puntos=(t // 15) % 4)
        # cartelito de lugar
        ui_marco(s, 6, 6, ui_ancho("DIRESA LA LIBERTAD · CENTRO DE SALUD") + 12, 14, borde=UI_ORO)
        s.blit(ui_texto("DIRESA LA LIBERTAD · CENTRO DE SALUD", UI_CREMA), (12, 9))

    # Escena 2: Consultorio. Dos historiales del mismo paciente que no coinciden.
    def _cine_consultorio(self, s, t):
        s.blit(self.salas["consultorio"], (0, 0))
        ciclo = t % 560
        jer = self.npc_by_id["jeremy"]
        if ciclo < 110:                                         # busca entre los cuadernos
            xj = 175 + math.sin(ciclo * 0.07) * 28
            flip = math.cos(ciclo * 0.07) > 0
            self._c_npc(s, "jeremy", xj, -((ciclo // 8) % 2), flip=flip)
        else:
            self._c_npc(s, "jeremy", 168, -((t // 40) % 2), flip=True)
        if ciclo < 110:
            self._particulas(s, jer, xj + SPRITE // 2, GROUND - FEET, 2)
        for k, (x_fin, x_ini, ini, texto, dni) in enumerate(((106, -70, 110, "PEREZ JUAN", "DNI 4821"),
                                                              (216, 390, 190, "PEREZ J.", "DNI 4812"))):
            if ciclo >= ini:
                p = min(1.0, (ciclo - ini) / 40)
                p = 1 - (1 - p) ** 3
                x = int(x_ini + (x_fin - x_ini) * p)
                _c_hoja(s, x, 72, 64, 44, lineas=0)
                s.blit(ui_texto(texto, UI_LINEA, sombra=None), (x + 4, 77))
                s.blit(ui_texto(dni, (60, 80, 150), sombra=None), (x + 4, 87))
                for q in range(3):
                    pygame.draw.rect(s, (150, 156, 176), (x + 4, 98 + q * 5, 56 - q * 8, 1))
                tinta = (200, 60, 70) if k else (60, 80, 150)
                pygame.draw.rect(s, tinta, (x + 4, 112 - 0, 12, 1))
        if ciclo >= 235:
            pop = 1 + (0.25 if ciclo < 255 else 0)
            _c_no_igual(s, 195, 94, 2)
        if ciclo >= 280:
            _c_globo(s, 168 + SPRITE // 2 - 3, GROUND - FEET - 17, "!", (200, 60, 70))

    # Escena 3: Farmacia. El cuaderno dice una cosa y el estante otra.
    def _cine_farmacia(self, s, t):
        s.blit(self.salas["farmacia"], (0, 0))
        ciclo = t % 620
        pat = self.npc_by_id["patroclo"]
        self._c_npc(s, "patroclo", 76, -((t // 14) % 2) if ciclo < 300 else (-3 if (t // 12) % 2 else 0), flip=True)
        self._particulas(s, pat, 76 + SPRITE // 2, GROUND - FEET, 2)
        cuantas = min(9, ciclo // 28)
        for k in range(cuantas):                                 # cuenta las cajas del estante
            _c_caja(s, 150 + k * 13, 124, k)
        # lo que dice el cuaderno
        if ciclo >= 30:
            _c_hoja(s, 62, 52, 56, 44, lineas=0)
            _c_cuaderno(s, 70, 56, 22, 12)
            n12 = ui_texto("12", UI_LINEA, sombra=None)
            s.blit(pygame.transform.scale(n12, (n12.get_width() * 3, n12.get_height() * 3)), (74, 70))
        # lo que hay en el estante
        if ciclo >= 290:
            _c_hoja(s, 268, 52, 56, 44, lineas=0)
            _c_caja(s, 276, 58, 0)
            n9 = ui_texto("9", UI_LINEA, sombra=None)
            s.blit(pygame.transform.scale(n9, (n9.get_width() * 3, n9.get_height() * 3)), (294, 70))
        if ciclo >= 340:
            _c_no_igual(s, 196, 76, 2)
        if ciclo >= 390:
            _c_globo(s, 76 + SPRITE // 2 - 3, GROUND - FEET - 17, "?", (200, 60, 70))

    # Escena 4: Sistemas TI. Archivos de Excel por todos lados.
    def _cine_admin(self, s, t):
        s.blit(self.salas["admin"], (0, 0))
        ciclo = t % 560
        # pantallas con hojas de cálculo
        for mx0 in (249, 291):
            pygame.draw.rect(s, (236, 244, 236), (mx0 + 2, 123, 31, 16))
            pygame.draw.rect(s, (46, 140, 78), (mx0 + 2, 123, 31, 3))
            for gx in range(mx0 + 2, mx0 + 33, 6):
                pygame.draw.rect(s, (150, 186, 156), (gx, 126, 1, 13))
            for gy in range(129, 139, 4):
                pygame.draw.rect(s, (150, 186, 156), (mx0 + 2, gy, 31, 1))
            if (t // 10) % 3 == 0:
                pygame.draw.rect(s, (255, 226, 130), (mx0 + 8 + (t // 10) % 5 * 5, 130, 6, 3))
        destinos = [(96, 52), (136, 40), (176, 58), (214, 44), (126, 84), (170, 96), (214, 86), (250, 66)]
        for k, (dx, dy) in enumerate(destinos):                   # los archivos salen volando del archivero
            ini = 30 + k * 42
            if ciclo < ini:
                continue
            p = min(1.0, (ciclo - ini) / 36)
            p = 1 - (1 - p) ** 2
            x = 90 + (dx - 90) * p
            y = 140 + (dy - 140) * p - math.sin(p * 3.14) * 18
            flot = math.sin(t * 0.05 + k) * 2 if p >= 1 else 0
            _c_archivo(s, int(x), int(y + flot))
        leo = self.npc_by_id["leonidas"]
        self._c_npc(s, "leonidas", 214, -((t // 5) % 2), flip=True)
        self._particulas(s, leo, 214 + SPRITE // 2, GROUND - FEET, 2)
        if ciclo >= 380:
            _c_globo(s, 214 + SPRITE // 2 - 3, GROUND - FEET - 17, "!", (200, 60, 70))

    # Escena 5: Administración. El reporte nunca llega a tiempo.
    def _cine_direccion(self, s, t):
        s.blit(self.salas["direccion"], (0, 0))
        ciclo = t % 560
        ari = self.npc_by_id["arian"]
        golpe = -1 if (t // 14) % 2 else 0
        self._c_npc(s, "arian", 150, golpe, flip=True)
        self._particulas(s, ari, 150 + SPRITE // 2, GROUND - FEET, 2)
        # calendario que pasa los días
        dia = min(30, 1 + ciclo // 9)
        temblor = (1 if (t // 3) % 2 else -1) if dia >= 30 else 0
        cx0 = 258 + temblor
        pygame.draw.rect(s, UI_LINEA, (cx0 - 1, 52, 52, 56))
        pygame.draw.rect(s, (250, 250, 246), (cx0, 53, 50, 54))
        pygame.draw.rect(s, (214, 60, 70), (cx0, 53, 50, 11))
        for rx in (cx0 + 8, cx0 + 38):
            pygame.draw.rect(s, UI_LINEA, (rx, 49, 3, 8))
        num = ui_texto(str(dia), UI_LINEA, sombra=None)
        num = pygame.transform.scale(num, (num.get_width() * 4, num.get_height() * 4))
        s.blit(num, (cx0 + (50 - num.get_width()) // 2, 70))
        # el reporte vacío en la mesa
        _c_hoja(s, 206, 126, 20, 26, lineas=0)
        for q in range(2):
            pygame.draw.rect(s, (200, 204, 216), (209, 130 + q * 4, 14, 1))
        if ciclo >= 300:
            _c_globo(s, 150 + SPRITE // 2 - 3, GROUND - FEET - 17, "!", (200, 60, 70))
            _c_equis(s, 216, 140, 2)

    # Escena 6: Reuniones. El MINSA no puede comprobar nada.
    def _cine_reuniones(self, s, t):
        s.blit(self.salas["reuniones"], (0, 0))
        ciclo = t % 560
        sel = min(3, ciclo // 90)
        for k, x in enumerate((196, 236, 276)):
            alto = 4 if (sel == k and ciclo % 90 > 8) else 0
            _c_hoja(s, x, 119 - alto, 22, 24, lineas=3)
            if sel > k or (sel == k and ciclo % 90 > 40):
                _c_equis(s, x + 11, 113 - alto, 2)
        self._c_npc(s, "carmen", 128, 0, flip=True if (ciclo < 270 or (ciclo // 18) % 2) else False)
        if ciclo >= 290:
            _c_globo(s, 128 + SPRITE // 2 - 3, GROUND - FEET - 17, "?", (200, 60, 70))


# ============================================================================
# PANTALLA DE INICIO (menú + ciudad) Y CINEMÁTICA DEL CONTEXTO PROBLEMÁTICO
# ============================================================================
TITULO_TXT = "DIRESA"
SUBTITULO_TXT = "THE GAME"
BOTONES_INICIO = ("JUGAR", "SALIR")
BTN_X, BTN_W, BTN_H = 144, 96, 17
BTN_Y = (142, 163)                       # arriba de cada botón (en píxeles internos 384x216)

# Cinemática: cada escena es una sala con su stakeholder haciendo lo suyo (casi sin texto).
CINE_ESCENAS = ["admision", "consultorio", "farmacia", "admin", "direccion", "reuniones"]
CAPITULO1_TARJETA = ("CAPÍTULO 1", "EL CENTRO DE SALUD DE PAPEL")

# Diagramas que se abren desde el juego: guarda los archivos en la carpeta "diagramas" (junto a main.py).
# El nombre del archivo debe EMPEZAR con la clave (da igual mayúsculas, espacios, _ o la extensión).
DIAGRAMAS = {
    "bpmn": ("EL DIAGRAMA BPMN DE LA RECTIFICACIÓN DE UN REGISTRO CLÍNICO", "BPMN"),
    "casosdeuso": ("EL DIAGRAMA DE CASOS DE USO", "CASOS DE USO"),
    "clases": ("EL DIAGRAMA DE CLASES", "CLASES"),
}


def buscar_diagrama(clave):
    """Devuelve la ruta del archivo del diagrama o None si no está en la carpeta diagramas."""
    carpetas = []
    if getattr(sys, "frozen", False):
        carpetas.append(os.path.join(os.path.dirname(sys.executable), "diagramas"))
    carpetas.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagramas"))
    carpetas.append(res("diagramas"))
    for c in carpetas:
        if not os.path.isdir(c):
            continue
        for f in sorted(os.listdir(c)):
            nombre, ext = os.path.splitext(f)
            if ext.lower() in (".txt", ".md", ""):
                continue
            if re.sub(r"[^a-z0-9]", "", nombre.lower()).startswith(clave):
                return os.path.join(c, f)
    return None


def abrir_archivo(ruta):
    """Abre el archivo con el programa que tenga tu computadora para ese tipo. True si pudo."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(ruta)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", ruta])
        else:
            subprocess.Popen(["xdg-open", ruta])
        return True
    except Exception:
        return False


def _lerp_c(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _texto_grande(txt, esc, color, claro=None, borde=UI_LINEA):
    """Texto pixel art grande, con contorno oscuro, sombra abajo y brillo arriba."""
    tilde = any(ch in ACENTOS for ch in _limpiar(txt))          # las tildes ocupan las 2 filas de arriba
    y0, alto = (0, 9) if tilde else (2, 7)
    base = ui_texto(txt, color, sombra=None).subsurface((0, y0, ui_ancho(txt) + 2, alto)).copy()
    w, h = base.get_width() * esc, base.get_height() * esc
    big = pygame.transform.scale(base, (w, h))
    sil = pygame.mask.from_surface(big).to_surface(setcolor=tuple(borde) + (255,), unsetcolor=(0, 0, 0, 0))
    out = pygame.Surface((w + esc * 4, h + esc * 5), pygame.SRCALPHA)
    ox, oy = esc * 2, esc * 2
    for dx in (-esc, 0, esc):
        for dy in (-esc, 0, esc):
            out.blit(sil, (ox + dx, oy + dy))
    out.blit(sil, (ox, oy + esc * 2))
    out.blit(big, (ox, oy))
    if claro:
        luz = pygame.transform.scale(ui_texto(txt, claro, sombra=None).subsurface((0, y0, ui_ancho(txt) + 2, alto)).copy(), (w, h))
        out.blit(luz, (ox, oy), area=(0, 0, w, esc * (3 + (2 if tilde else 0))))
    return out


def crear_fondo_ciudad():
    """Dibuja (una sola vez) el cielo, las capas de edificios y la calle de la pantalla de inicio."""
    import random
    r = random.Random(11)
    cielo = pygame.Surface((W, H))
    paradas = [(0.0, (10, 14, 40)), (0.35, (30, 32, 84)), (0.58, (96, 54, 118)),
               (0.80, (214, 104, 112)), (1.0, (255, 176, 112))]
    for y in range(0, H, 3):
        f = min(1.0, y / 165)
        for (f0, c0), (f1, c1) in zip(paradas, paradas[1:]):
            if f0 <= f <= f1:
                col = _lerp_c(c0, c1, (f - f0) / (f1 - f0))
                break
        pygame.draw.rect(cielo, col, (0, y, W, 3))
    estrellas = [(r.randrange(W), r.randrange(0, 95), r.random() * 6.28) for _ in range(70)]
    # luna
    pygame.draw.circle(cielo, (244, 240, 214), (352, 30), 13)
    pygame.draw.circle(cielo, (222, 216, 190), (347, 26), 3)
    pygame.draw.circle(cielo, (222, 216, 190), (357, 36), 2)
    pygame.draw.circle(cielo, (228, 224, 198), (356, 24), 2)

    def capa(color, hmin, hmax, base, luz, prob, azotea):
        s = pygame.Surface((W * 2, H), pygame.SRCALPHA)
        x = 0
        while x < W:
            ancho = min(r.randrange(16, 34), W - x)
            if W - x < 16:
                ancho = W - x
            alto = r.randrange(hmin, hmax)
            top = base - alto
            for dx in (0, W):
                pygame.draw.rect(s, color, (x + dx, top, ancho, alto + 40))
                if azotea and r.random() < 0.4:                      # antenita
                    pygame.draw.rect(s, color, (x + dx + ancho // 2, top - 6, 1, 6))
            for wy in range(top + 5, base - 4, 7):
                for wx in range(x + 3, x + ancho - 3, 6):
                    if r.random() < prob:
                        c = luz if r.random() < 0.8 else (255, 236, 170)
                        for dx in (0, W):
                            pygame.draw.rect(s, c, (wx + dx, wy, 3, 3))
            x += ancho
        return s

    lejos = capa((62, 46, 104), 36, 84, 172, (170, 122, 150), 0.18, False)
    medio = capa((36, 30, 74), 56, 118, 178, (255, 204, 108), 0.34, True)

    cerca = pygame.Surface((W, H), pygame.SRCALPHA)
    # edificio oscuro a la izquierda
    pygame.draw.rect(cerca, (22, 24, 50), (0, 92, 58, 100))
    pygame.draw.rect(cerca, (30, 32, 62), (0, 92, 58, 4))
    for wy in range(102, 182, 12):
        for wx in (7, 24, 41):
            c = (255, 208, 112) if r.random() < 0.55 else (46, 52, 90)
            pygame.draw.rect(cerca, c, (wx, wy, 8, 7))
    # el centro de salud (a la derecha)
    cx0, cy0, cw, ch = 292, 118, 84, 70
    pygame.draw.rect(cerca, (18, 20, 44), (cx0 - 2, cy0 - 2, cw + 4, ch + 4))
    pygame.draw.rect(cerca, (222, 226, 238), (cx0, cy0, cw, ch))
    pygame.draw.rect(cerca, (186, 192, 214), (cx0, cy0, cw, 6))
    pygame.draw.rect(cerca, (186, 192, 214), (cx0, cy0 + ch - 8, cw, 8))
    for wx in (cx0 + 8, cx0 + 30, cx0 + 52, cx0 + 70):
        pygame.draw.rect(cerca, (18, 20, 44), (wx - 1, cy0 + 14, 12, 14))
        pygame.draw.rect(cerca, (255, 226, 150), (wx, cy0 + 15, 10, 12))
        pygame.draw.rect(cerca, (222, 226, 238), (wx + 4, cy0 + 15, 1, 12))
    pygame.draw.rect(cerca, (18, 20, 44), (cx0 + 30, cy0 + 40, 24, 30))
    pygame.draw.rect(cerca, (110, 170, 214), (cx0 + 32, cy0 + 42, 9, 28))
    pygame.draw.rect(cerca, (110, 170, 214), (cx0 + 43, cy0 + 42, 9, 28))
    # cartel con la cruz roja
    pygame.draw.rect(cerca, (18, 20, 44), (cx0 + 28, cy0 - 18, 28, 18))
    pygame.draw.rect(cerca, (250, 250, 250), (cx0 + 30, cy0 - 16, 24, 14))
    pygame.draw.rect(cerca, (214, 48, 58), (cx0 + 40, cy0 - 14, 4, 10))
    pygame.draw.rect(cerca, (214, 48, 58), (cx0 + 37, cy0 - 11, 10, 4))
    # vereda y calle
    pygame.draw.rect(cerca, (74, 76, 104), (0, 188, W, 6))
    pygame.draw.rect(cerca, (46, 48, 72), (0, 188, W, 1))
    pygame.draw.rect(cerca, (32, 32, 52), (0, 194, W, H - 194))
    for x in range(0, W, 32):
        pygame.draw.rect(cerca, (120, 120, 140), (x + 6, 206, 16, 2))
    return dict(cielo=cielo, estrellas=estrellas, lejos=lejos, medio=medio, cerca=cerca, postes=(30, 150, 270, 372))


# ---- dibujitos para la cinemática ----------------------------------------------------------------
def _c_hoja(s, x, y, w=9, h=11, color=(250, 250, 246), lineas=3, lc=(150, 156, 176)):
    pygame.draw.rect(s, UI_LINEA, (x - 1, y - 1, w + 2, h + 2))
    pygame.draw.rect(s, color, (x, y, w, h))
    for k in range(lineas):
        yy = y + 2 + k * 3
        if yy < y + h - 1:
            pygame.draw.rect(s, lc, (x + 1, yy, w - 3 - (k % 2) * 2, 1))


def _c_globo(s, cx, top, glyph, col=UI_LINEA, puntos=None):
    """Globito de pensamiento con '?', '!' o '...'. cx = centro, top = arriba."""
    x, w, h = int(cx) - 8, 17, 13
    pygame.draw.rect(s, UI_LINEA, (x, top, w, h))
    pygame.draw.rect(s, (252, 252, 250), (x + 1, top + 1, w - 2, h - 2))
    pygame.draw.rect(s, UI_LINEA, (x + 6, top + h, 3, 2))
    pygame.draw.rect(s, (252, 252, 250), (x + 7, top + h - 1, 1, 1))
    if puntos is not None:
        for k in range(puntos):
            pygame.draw.rect(s, UI_LINEA, (x + 4 + k * 4, top + 8, 2, 2))
    else:
        g = ui_texto(glyph, col, sombra=None)
        s.blit(g, (x + (w - (g.get_width() - 2)) // 2 - 0, top + 1))


def _c_no_igual(s, cx, cy, esc=1, col=(228, 70, 70)):
    for dx, dy, c in ((1, 1, UI_LINEA), (0, 0, col)):
        pygame.draw.rect(s, c, (cx - 6 * esc + dx, cy - 4 * esc + dy, 12 * esc, 2 * esc))
        pygame.draw.rect(s, c, (cx - 6 * esc + dx, cy + 1 * esc + dy, 12 * esc, 2 * esc))
        pygame.draw.line(s, c, (cx + 4 * esc + dx, cy - 8 * esc + dy), (cx - 4 * esc + dx, cy + 8 * esc + dy), max(2, esc * 2))


def _c_equis(s, cx, cy, esc=1, col=(228, 70, 70)):
    for dx, dy, c in ((1, 1, UI_LINEA), (0, 0, col)):
        pygame.draw.line(s, c, (cx - 4 * esc + dx, cy - 4 * esc + dy), (cx + 4 * esc + dx, cy + 4 * esc + dy), max(2, esc * 2))
        pygame.draw.line(s, c, (cx + 4 * esc + dx, cy - 4 * esc + dy), (cx - 4 * esc + dx, cy + 4 * esc + dy), max(2, esc * 2))


def _c_cuaderno(s, x, y, w=22, h=15):
    pygame.draw.rect(s, UI_LINEA, (x - 1, y - 1, w + 2, h + 2))
    pygame.draw.rect(s, (176, 124, 76), (x, y, w, h))
    pygame.draw.rect(s, (250, 248, 238), (x + 1, y + 1, w // 2 - 1, h - 2))
    pygame.draw.rect(s, (250, 248, 238), (x + w // 2 + 1, y + 1, w // 2 - 2, h - 2))
    for k in range(3):
        pygame.draw.rect(s, (130, 140, 170), (x + 2, y + 3 + k * 4, w // 2 - 4, 1))
        pygame.draw.rect(s, (130, 140, 170), (x + w // 2 + 2, y + 3 + k * 4, w // 2 - 5, 1))


def _c_archivo(s, x, y, ang=0):
    """Archivito de Excel (hoja con una X verde)."""
    pygame.draw.rect(s, UI_LINEA, (x - 1, y - 1, 13, 15))
    pygame.draw.rect(s, (250, 250, 246), (x, y, 11, 13))
    pygame.draw.rect(s, (46, 140, 78), (x, y, 11, 4))
    pygame.draw.line(s, (46, 140, 78), (x + 3, y + 6), (x + 7, y + 11), 1)
    pygame.draw.line(s, (46, 140, 78), (x + 7, y + 6), (x + 3, y + 11), 1)


def _c_caja(s, x, y, tono=0):
    col = ((236, 240, 244), (200, 232, 210), (240, 226, 200))[tono % 3]
    pygame.draw.rect(s, UI_LINEA, (x - 1, y - 1, 13, 12))
    pygame.draw.rect(s, col, (x, y, 11, 10))
    pygame.draw.rect(s, (60, 160, 90), (x + 4, y + 2, 3, 6))
    pygame.draw.rect(s, (60, 160, 90), (x + 2, y + 4, 7, 2))


# ----------------------------------------------------------------------------
# VOCES 8 BITS: cada personaje tiene su propio "blip" (onda, tono y duración).
# Se generan con código (sin archivos de audio), así que no hay que adjuntar nada.
# ----------------------------------------------------------------------------
TEXTO_VEL = 0.7            # letras por cuadro en la máquina de escribir (~42 letras por segundo)
VOCES = {                  # onda: cuadrada con "duty" (ancho de pulso) o triangular · tono en Hz
    "yo":        dict(onda=("pulso", 0.50), hz=520, ms=46),
    "jeremy":    dict(onda=("pulso", 0.25), hz=430, ms=44),
    "carmen":    dict(onda=("tri", 0), hz=640, ms=48),
    "patroclo":  dict(onda=("pulso", 0.50), hz=300, ms=52),
    "yasuri":    dict(onda=("pulso", 0.125), hz=720, ms=40),
    "sara":      dict(onda=("tri", 0), hz=560, ms=46),
    "leonidas":  dict(onda=("pulso", 0.25), hz=250, ms=50),
    "arian":     dict(onda=("pulso", 0.50), hz=205, ms=56),
    "mariajose": dict(onda=("pulso", 0.125), hz=610, ms=44),
}


class Voces:
    RATE = 22050

    def __init__(self):
        self.ok = False
        self.activo = True
        self.cache = {}
        self.cuenta = 0
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(self.RATE, -16, 1, 512)
            ini = pygame.mixer.get_init()                       # (frecuencia, formato, canales)
            self.rate, self.canales = ini[0], ini[2]
            self.ok = ini[1] == -16

        except Exception:
            self.ok = False

    def _onda(self, cfg, hz, ms):
        import array
        n = int(self.rate * ms / 1000)
        datos = array.array("h")
        tipo, duty = cfg["onda"]
        for i in range(n):
            fase = (i * hz / self.rate) % 1.0
            if tipo == "tri":
                v = 4 * abs(fase - 0.5) - 1
            else:
                v = (2 - 2 * duty if fase < duty else -2 * duty) / max(2 - 2 * duty, 2 * duty)   # sin "clic" de offset
            env = min(1.0, i / 90) * (1 - i / n) ** 0.7              # sube rápido y se apaga
            dato = int(v * env * 5200)
            for _ in range(self.canales):                       # mono o estéreo, según el mezclador
                datos.append(dato)
        return pygame.mixer.Sound(buffer=datos.tobytes())

    def _sonidos(self, quien):
        if quien not in self.cache:
            cfg = VOCES.get(quien, VOCES["yo"])
            self.cache[quien] = [self._onda(cfg, cfg["hz"] * f, cfg["ms"]) for f in (0.94, 1.0, 1.09)]
        return self.cache[quien]

    def letra(self, quien):
        """Llamar cada vez que aparece una letra; suena una de cada 3."""
        if not (self.ok and self.activo):
            return
        self.cuenta += 1
        if self.cuenta % 3:
            return
        try:
            random.choice(self._sonidos(quien)).play()
        except Exception:
            self.ok = False


def main():
    pygame.init()
    pygame.display.set_caption("DIRESA: The Game")
    flags = pygame.SCALED | pygame.RESIZABLE
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
    clock = pygame.time.Clock()
    game = Game()
    game.iniciar_con_menu()
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                elif game.tecla(e.key) == "salir":      # E, TAB, ESC y el menú del buzón
                    running = False
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if game.clic(e.pos) == "salir":
                    running = False
        k = pygame.key.get_pressed()
        corriendo = k[pygame.K_LSHIFT] or k[pygame.K_RSHIFT]
        if game.menu is None:
            game.update(k[pygame.K_LEFT] or k[pygame.K_a], k[pygame.K_RIGHT] or k[pygame.K_d],
                        k[pygame.K_UP] or k[pygame.K_w], k[pygame.K_DOWN] or k[pygame.K_s],
                        run=corriendo)
        else:
            game.update(False, False, run=False)                     # con el menú abierto no te mueves
        game.render(screen)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__":
    main()
