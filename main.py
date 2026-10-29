import math
import os
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

# kind: aspecto del muñequito de prueba (hasta que tengas su PNG)
# poder / interes / cuadrante: Tabla 6 del informe (2.4 Matriz de poder/interés)
# actividad: lo que hace el personaje en el hospital (baila, signos, pasea, teclea, inspecciona, acomoda, telefono)
# need y says se guardan para los capítulos de requisitos y conflictos
NPCS = [
    dict(id="diresa",   x=2760, name="DIRESA La Libertad", role="Patrocinador del proyecto",
         poder="Alto", interes="Alto", cuadrante="Gestionar de cerca", actividad="telefono",
         need="Decide qué módulos se priorizan",
         body=(122, 34, 48), accent=(75, 22, 32), kind="suit"),
    dict(id="admin",    x=1560, name="Equipo de TI / Administración", role="Administración de sistemas",
         poder="Alto", interes="Alto", cuadrante="Gestionar de cerca", actividad="teclea",
         need="Trazabilidad legal (NTS 139)",
         body=(92, 92, 110), accent=(54, 54, 63), kind="suit", conflict="c1",
         says="¡Todo cambio debe quedar registrado!"),
    dict(id="minsa",    x=2400, name="MINSA", role="Órgano rector (NTS 139)",
         poder="Alto", interes="Medio", cuadrante="Mantener satisfecho", actividad="inspecciona",
         need="Cumplimiento de la NTS 139",
         body=(44, 92, 128), accent=(28, 58, 84), kind="suit"),
    dict(id="jeremy",   x=1330, name="Dr. Jeremy Armas", role="Médico General",
         poder="Bajo", interes="Alto", cuadrante="Mantener informado", actividad="pasea",
         need="Rapidez: atender en 5 clics o menos",
         body=(238, 241, 241), accent=(154, 167, 167), kind="doctor", conflict="c1",
         says="¡Necesito atender rápido, en 5 clics!"),
    dict(id="sara",     x=840,  name="Sra. Sara Acuy", role="Enfermería (Triaje)",
         poder="Bajo", interes="Alto", cuadrante="Mantener informado", actividad="signos",
         need="Registro rápido de signos vitales",
         body=(47, 158, 143), accent=(30, 106, 96), kind="nurse"),
    dict(id="farmacia", x=1980, name="Técnico de Farmacia", role="Dispensación de recetas",
         poder="Bajo", interes="Alto", cuadrante="Mantener informado", actividad="acomoda",
         need="Control estricto del kárdex",
         body=(79, 143, 63), accent=(47, 92, 38), kind="apron", conflict="c2",
         says="¡Cada salida debe ir al kárdex!"),
    dict(id="patroclo", x=300,  name="Sr. Patroclo Suarez", role="Paciente",
         poder="Bajo", interes="Bajo", cuadrante="Monitorear", actividad="baila",
         need="Atención sin errores de transcripción",
         body=(68, 114, 168), accent=(44, 79, 120), kind="normal", conflict="c2",
         says="¡No queremos hacer cola!"),
]

CONFLICTS = {
    "c1": dict(members=("jeremy", "admin"),
               label="Médicos vs. Administración/MINSA",
               resolution="Resuelto: Inmutabilidad + Adenda Ágil (4.85/5, consenso)"),
    "c2": dict(members=("farmacia", "patroclo"),
               label="Farmacia vs. Pacientes/Médicos",
               resolution="Resuelto: Cola virtual, despacho en 1 clic (4.80/5, consenso)"),
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
}

# cada sala: nombre, stakeholder que vive ahí, dónde está parado en el plano (map_pos)
# y dónde está parado dentro de la sala de perfil (x)
SALAS = {
    "admision":    dict(name="Admisión",              npc="minsa",    map_pos=(64, 434),  x=284),
    "triaje":      dict(name="Triaje",                npc="sara",     map_pos=(236, 256), x=236),
    "consultorio": dict(name="Consultorio",           npc="jeremy",   map_pos=(266, 64),  x=222),
    "admin":       dict(name="Administración · TI",   npc="admin",    map_pos=(84, 60),   x=176),
    "farmacia":    dict(name="Farmacia",              npc="farmacia", map_pos=(560, 266), x=286),
    "espera":      dict(name="Sala de espera",        npc="patroclo", map_pos=(556, 476), x=258),
    "direccion":   dict(name="Dirección · DIRESA",    npc="diresa",   map_pos=(444, 44),  x=228),
}

# ----------------------------------------------------------------------------
# CAPÍTULOS (se eligen en el buzón que está a la izquierda del hospital)
# ----------------------------------------------------------------------------
CAPITULOS = [
    dict(titulo="Conociendo a los stakeholders", mision="Conoce a los 7 stakeholders",
         logro="Conociendo a los stakeholders"),
    dict(titulo="Requisitos de cada stakeholder", mision="Próximamente", logro=None),
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
                self.show_banner("Adentro del hospital: acércate a cada persona")
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
                    self.show_banner("¡Recorrido completo! 7 stakeholders identificados")

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
        zi = self.f_med.render("Exterior · Hospital", True, (240, 180, 41))
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
            self.show_banner("¡Recorrido completo! 7 stakeholders identificados")

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
            zona = "Hospital · Pasillos"
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
        """Conoces a un stakeholder. Al conocer a los 7 se gana el logro del Capítulo 1."""
        self.collected.append(n["id"])
        self.show_banner(f"{n['name']}: stakeholder identificado")
        if len(self.collected) == len(NPCS) and self.capitulo == 1:
            self._logro(CAPITULOS[0]["logro"])
            self.desbloqueados = max(self.desbloqueados, 2)
            self.buzon_nuevo = True
            self.show_banner("¡Misión cumplida! Sal del hospital y revisa el buzón")

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
    def _pose(self, n):
        """Movimiento según la actividad: (dx, dy, voltear). En píxeles del plano.
        voltear = None significa 'que mire hacia ti' (en las salas)."""
        t = self.t + self._fase.get(n["id"], 0)
        act = n.get("actividad", "")
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
        return 0, int(math.sin(t * 0.07)), None

    def _particulas(self, s, n, cx, top, esc):
        """Partículas alrededor de cada stakeholder. cx = centro, top = arriba del dibujo, esc = 1 plano / 2 sala."""
        t = self.t + self._fase.get(n["id"], 0)
        act = n.get("actividad", "")
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
        # retratos de los 7 stakeholders (progreso)
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
        filas = 3 if self.scene != "ext" else 2
        w_mover = 8 + len(teclas) * 13 + ui_ancho("MOVER") + 6
        activo = getattr(self, "correr_toggle", False)
        txt_correr = "CORRER (ON)" if activo else "CORRER"
        w_correr = 10 + ui_ancho("SHIFT") + 6 + 5 + ui_ancho(txt_correr) + 6
        w = max(w_mover, w_correr)
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
        if filas == 3:
            y += 14
            kx = ui_tecla(s, 10, y, "TAB")
            s.blit(ui_texto("PANEL", UI_GRIS), (10 + kx + 5, y + 2))

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
            zona = "Exterior · Hospital"
            if libre and self.near_door():
                pregunta = "ENTRAR"
            elif libre and self.cerca_buzon():
                pregunta = "VER CAPÍTULOS"
        elif self.scene == "map":
            cx, cy = self.cam_mapa()
            zona = "Hospital · Pasillos"
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

def main():
    pygame.init()
    pygame.display.set_caption("Recorrido de Stakeholders · DIRESA La Libertad")
    flags = pygame.SCALED | pygame.RESIZABLE
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
    clock = pygame.time.Clock()
    game = Game()
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
