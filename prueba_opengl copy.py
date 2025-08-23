# Requiere: PyOpenGL, Pillow
import sys
import os
import random
from PIL import Image
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from collections import defaultdict
import time
import threading


fullscreen = True
screen_width = 800  # Valores por defecto, se ajustarán tras glutInit
screen_height = 600

backgrounds = ['background1.jpg', 'background2.jpg']
current_bg_index = 0
bg_textures = []

gif_mapping = {
    b'a': 'espana-spain.gif',
    b's': 'calamardo.gif',
    b'd': 'calamardo2.gif'
}


active_gifs = defaultdict(list)
clock = None

# Utilidades para cargar imágenes como texturas

def load_texture(image_path):
    img = Image.open(image_path).convert('RGBA')
    img_data = img.tobytes()
    width, height = img.size
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    return tex_id, width, height



# Cola de GIFs pendientes de inicializar texturas en el hilo principal
pending_gifs = []

class BouncingGIF:
    def __init__(self, gif_path, on_ready=None):
        self.frames = []
        self.sizes = []
        self.index = 0
        self.width = 1
        self.height = 1
        self.x = 0
        self.y = 0
        self.dx = 5
        self.dy = 5
        self.ready = False
        self._gif_path = gif_path
        self._on_ready = on_ready
        self._pil_frames = []
        threading.Thread(target=self._load_gif_pil_frames, daemon=True).start()

    def _load_gif_pil_frames(self):
        gif = Image.open(self._gif_path)
        for frame in range(gif.n_frames):
            gif.seek(frame)
            frame_img = gif.convert('RGBA').copy()
            self._pil_frames.append(frame_img)
        # Marcar para inicializar texturas en el hilo principal
        pending_gifs.append(self)

    def init_textures(self):
        # Llamar solo en el hilo principal
        for frame_img in self._pil_frames:
            tex_id, w, h = load_texture_from_pil(frame_img)
            self.frames.append(tex_id)
            self.sizes.append((w, h))
        self.index = 0
        self.width, self.height = self.sizes[0]
        self.x = random.randint(0, screen_width - self.width)
        self.y = random.randint(0, screen_height - self.height)
        self.ready = True
        if self._on_ready:
            self._on_ready(self)
        self._pil_frames = []  # Liberar memoria

    def update(self):
        if not self.ready:
            return
        self.index = (self.index + 1) % len(self.frames)
        self.width, self.height = self.sizes[self.index]
        self.x += self.dx
        self.y += self.dy
        if self.x <= 0 or self.x + self.width >= screen_width:
            self.dx *= -1
        if self.y <= 0 or self.y + self.height >= screen_height:
            self.dy *= -1

    def draw(self):
        if not self.ready:
            return
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.frames[self.index])
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(self.x, self.y)
        glTexCoord2f(1, 0); glVertex2f(self.x + self.width, self.y)
        glTexCoord2f(1, 1); glVertex2f(self.x + self.width, self.y + self.height)
        glTexCoord2f(0, 1); glVertex2f(self.x, self.y + self.height)
        glEnd()
        glDisable(GL_TEXTURE_2D)

def load_texture_from_pil(img):
    img_data = img.tobytes()
    width, height = img.size
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    return tex_id, width, height

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    # Fondo
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, bg_textures[current_bg_index][0])
    w, h = bg_textures[current_bg_index][1:]
    glColor4f(1, 1, 1, 1)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(0, 0)
    glTexCoord2f(1, 0); glVertex2f(screen_width, 0)
    glTexCoord2f(1, 1); glVertex2f(screen_width, screen_height)
    glTexCoord2f(0, 1); glVertex2f(0, screen_height)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    # GIFs activos
    for gif_list in active_gifs.values():
        for gif in gif_list:
            gif.draw()
    glutSwapBuffers()

def idle():
    # Inicializar texturas de GIFs pendientes (en el hilo principal)
    global pending_gifs
    if pending_gifs:
        for gif in pending_gifs[:]:
            if gif._pil_frames:
                gif.init_textures()
                pending_gifs.remove(gif)
    for gif_list in active_gifs.values():
        for gif in gif_list:
            gif.update()
    glutPostRedisplay()
    time.sleep(1/30)  # Limita a 30 FPS

def keyboard(key, x, y):
    global current_bg_index
    mods = glutGetModifiers()
    # ESC para salir
    if key == b'\x1b':
        try:
            glutLeaveMainLoop()
        except Exception:
            sys.exit()
    # Ignorar teclas especiales
    elif key == b'\xe0':
        pass
    # Flecha derecha
    elif key == b'\x27':
        current_bg_index = (current_bg_index + 1) % len(bg_textures)
    # Flecha izquierda
    elif key == b'\x25':
        current_bg_index = (current_bg_index - 1) % len(bg_textures)
    # Shift + tecla: eliminar todos los GIFs de esa tecla
    elif (mods & GLUT_ACTIVE_SHIFT):
        key_lower = key.lower()
        if key_lower in gif_mapping:
            active_gifs[key_lower].clear()
    # Tecla normal: añadir un nuevo GIF (sin eliminar los anteriores)
    elif key in gif_mapping:
        gif_path = gif_mapping[key]
        if os.path.exists(gif_path):
            def add_gif(gif_obj):
                # Solo añadir si ya está listo (por seguridad)
                if gif_obj.ready:
                    active_gifs[key].append(gif_obj)
                else:
                    # Si no, se añadirá automáticamente tras init_textures
                    pass
            BouncingGIF(gif_path, on_ready=add_gif)

def reshape(width, height):
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, width, height, 0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

def main():
    global bg_textures, screen_width, screen_height
    glutInit(sys.argv)
    screen_width = glutGet(GLUT_SCREEN_WIDTH)
    screen_height = glutGet(GLUT_SCREEN_HEIGHT)
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_ALPHA | GLUT_DEPTH)
    glutInitWindowSize(screen_width, screen_height)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b'OpenGL Backgrounds & GIFs')
    if fullscreen:
        glutFullScreen()
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    # Cargar fondos
    for bg in backgrounds:
        tex_id, w, h = load_texture(bg)
        bg_textures.append((tex_id, w, h))
    glutDisplayFunc(display)
    glutIdleFunc(idle)
    glutKeyboardFunc(keyboard)
    glutReshapeFunc(reshape)
    glutMainLoop()

if __name__ == '__main__':
    main()
