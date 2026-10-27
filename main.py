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
PROX = 70                # distancia para "identificar" a un stakeholder
CONFLICT_PAD = 45
FRAME_TICKS = 8          # cada cuántos fotogramas cambia el cuadro de caminata
SPRITE = 32
HOSPITAL_CLOSED = "assets/hospital_cerrado.png"   # tu hospital con la puerta cerrada
HOSPITAL_OPEN = "assets/hospital_abierto.png"     # el mismo hospital con la puerta abierta
HOSPITAL_SCALE = 2       # ampliación del hospital: 1, 2 o 3 (números enteros = píxeles nítidos)
DOOR_X_IMG = 157         # dónde está el centro de la puerta dentro de la imagen (en píxeles de la imagen)


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
NPCS = [
    dict(id="patroclo",   x=300,  name="Sr. Patroclo Suarez",   role="Paciente",
         need="Atención sin errores de transcripción",
         body=(68, 114, 168), accent=(44, 79, 120), kind="normal"),
    dict(id="sara",       x=840,  name="Sra. Sara Acuy",        role="Enfermera (Triaje)",
         need="Registro rápido de signos vitales",
         body=(47, 158, 143), accent=(30, 106, 96), kind="nurse"),
    dict(id="jeremy",     x=1330, name="Dr. Jeremy Armas",      role="Médico General",
         need="Rapidez: atender en 5 clics o menos",
         body=(238, 241, 241), accent=(154, 167, 167), kind="doctor", conflict="c1",
         says="¡Necesito atender rápido, en 5 clics!"),
    dict(id="admin",      x=1560, name="Administración / MINSA", role="Equipo TI y regulador",
         need="Trazabilidad legal (NTS 139)",
         body=(92, 92, 110), accent=(54, 54, 63), kind="suit", conflict="c1",
         says="¡Todo cambio debe quedar registrado!"),
    dict(id="farmacia",   x=1980, name="Técnico de Farmacia",   role="Dispensación",
         need="Control estricto del kárdex",
         body=(79, 143, 63), accent=(47, 92, 38), kind="apron", conflict="c2",
         says="¡Cada salida debe ir al kárdex!"),
    dict(id="pacientes2", x=2200, name="Pacientes y médicos",   role="Usuarios de farmacia",
         need="Despacho sin colas",
         body=(168, 106, 158), accent=(111, 65, 102), kind="normal", conflict="c2",
         says="¡No queremos hacer cola!"),
    dict(id="diresa",     x=2760, name="DIRESA La Libertad",    role="Patrocinador (alto poder/interés)",
         need="Decide qué módulos se priorizan",
         body=(122, 34, 48), accent=(75, 22, 32), kind="suit"),
]

CONFLICTS = {
    "c1": dict(members=("jeremy", "admin"),
               label="Médicos vs. Administración/MINSA",
               resolution="Resuelto: Inmutabilidad + Adenda Ágil (4.85/5, consenso)"),
    "c2": dict(members=("farmacia", "pacientes2"),
               label="Farmacia vs. Pacientes/Médicos",
               resolution="Resuelto: Cola virtual, despacho en 1 clic (4.80/5, consenso)"),
}

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


def load_player_frames():
    frames = []
    for i in range(1, 5):
        im = pygame.image.load(res(f"assets/jugador_{i}.png")).convert_alpha()
        frames.append(im)
    return frames


def load_npc_sprites():
    out = {}
    for n in NPCS:
        p = res(f"assets/npc_{n['id']}.png")
        if os.path.exists(p):
            out[n["id"]] = pygame.image.load(p).convert_alpha()
        else:
            out[n["id"]] = make_npc_sprite(n["body"], n["accent"], n["kind"])
    return out


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

    def update(self, left, right):
        self.t += 1
        vx = (SPEED if right else 0) - (SPEED if left else 0)
        if self.trans is not None:
            vx = 0
            if self.trans["phase"] in ("open", "fadeout") and self.scene == "ext":
                target = self.door_cx - SPRITE / 2          # el personaje camina hasta la puerta
                if abs(target - self.px) > 1.5:
                    vx = SPEED * 0.8 * (1 if target > self.px else -1)
            self._update_trans()
        max_x = (W if self.scene == "ext" else WORLD_W) - SPRITE
        self.px = max(0, min(max_x, self.px + vx))
        self.bob += 0.12
        if vx:
            self.facing = 1 if vx > 0 else -1
            self.tick += 1
            if self.tick >= FRAME_TICKS:
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
            sy = GROUND - 30 + bob
            self._shadow(w, sx + SPRITE // 2, GROUND + 1)
            w.blit(img, (sx, sy))

        # jugador (tu dibujo mira a la izquierda, se voltea al ir a la derecha)
        img = self.player_frames[self.frame]
        if self.facing == 1:
            img = pygame.transform.flip(img, True, False)
        sx = int(self.px - cam)
        self._shadow(w, sx + SPRITE // 2, GROUND + 1)
        w.blit(img, (sx, GROUND - 30))

    @staticmethod
    def _shadow(w, cx, y):
        sh = pygame.Surface((22, 6), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 60), (0, 0, 22, 6))
        w.blit(sh, (cx - 11, y - 3))

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
            top = (GROUND - 30) * SCALE
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
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                elif e.key == pygame.K_e:
                    game.press_e()
        k = pygame.key.get_pressed()
        game.update(k[pygame.K_LEFT] or k[pygame.K_a], k[pygame.K_RIGHT] or k[pygame.K_d])
        game.render(screen)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()


if __name__ == "__main__":
    main()
