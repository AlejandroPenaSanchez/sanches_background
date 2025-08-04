# Versión OpenGL de prueba1.py
# Requiere: PyOpenGL, Pillow
import sys
import os
import random
from PIL import Image
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import time


fullscreen = True
screen_width = 800  # Valores por defecto, se ajustarán tras glutInit
screen_height = 600

backgrounds = ['background1.jpg', 'background2.jpg']
current_bg_index = 0
bg_textures = []

gif_mapping = {
    b'a': 'espana-spain.gif',
    b'b': 'calamardo.gif'
}

active_gifs = {}
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

class BouncingGIF:
    def __init__(self, gif_path):
        self.frames, self.sizes = self.load_gif_frames(gif_path)
        self.index = 0
        self.width, self.height = self.sizes[0]
        self.x = random.randint(0, screen_width - self.width)
        self.y = random.randint(0, screen_height - self.height)
        self.dx = 5
        self.dy = 5

    def load_gif_frames(self, gif_path):
        frames = []
        sizes = []
        gif = Image.open(gif_path)
        for frame in range(gif.n_frames):
            gif.seek(frame)
            frame_img = gif.convert('RGBA')
            tex_id, w, h = load_texture_from_pil(frame_img)
            frames.append(tex_id)
            sizes.append((w, h))
        return frames, sizes

    def update(self):
        self.index = (self.index + 1) % len(self.frames)
        self.width, self.height = self.sizes[self.index]
        self.x += self.dx
        self.y += self.dy
        if self.x <= 0 or self.x + self.width >= screen_width:
            self.dx *= -1
        if self.y <= 0 or self.y + self.height >= screen_height:
            self.dy *= -1

    def draw(self):
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
    for gif in active_gifs.values():
        gif.draw()
    glutSwapBuffers()

def idle():
    for gif in active_gifs.values():
        gif.update()
    glutPostRedisplay()
    time.sleep(1/30)  # Limita a 30 FPS

def keyboard(key, x, y):
    global current_bg_index
    if key == b'\x1b':  # ESC
        try:
            glutLeaveMainLoop()
        except Exception:
            sys.exit()
    elif key == b'\xe0':
        pass  # Ignore special keys
    elif key == b'\x27':  # Right arrow
        current_bg_index = (current_bg_index + 1) % len(bg_textures)
    elif key == b'\x25':  # Left arrow
        current_bg_index = (current_bg_index - 1) % len(bg_textures)
    elif key in gif_mapping:
        gif_path = gif_mapping[key]
        if os.path.exists(gif_path):
            active_gifs[key] = BouncingGIF(gif_path)

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
