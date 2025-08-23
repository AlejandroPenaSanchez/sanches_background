# Requiere: PyOpenGL, Pillow
import sys
import os
import random
import time
import threading
from PIL import Image
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from collections import defaultdict

FPS = 30
Backgrounds = ['./img/background1.jpg', './img/background2.jpg']
Gif_mapping = {
    b'a': {'path': './img/espana-spain.gif', 'stick_on_collision': False, 'max_width': 300, 'max_height': 300},
    b's': {'path': './img/calamardo.gif', 'stick_on_collision': False, 'max_width': 300, 'max_height': 300 },
    b'd': {'path': './img/calamardo2.gif', 'stick_on_collision': False, 'max_width': 300, 'max_height': 300 },
    b'z': {'path': './img/trosky.jpg', 'stick_on_collision': True, 'max_width': 300, 'max_height': 300, 'colision_tipo': 'cabeza'},
    b'x': {'path': './img/piolet.png', 'stick_on_collision': True, 'max_width': 300, 'max_height': 300, 'colision_tipo': 'piolet'}
}

class BackgroundManager:
    def __init__(self, backgrounds):
        self.backgrounds = backgrounds
        self.textures = []
        self.current_index = 0

    def load_textures(self):
        self.textures = []
        for bg in self.backgrounds:
            tex_id, w, h = self.load_texture(bg)
            self.textures.append((tex_id, w, h))

    def load_texture(self, image_path):
        img = Image.open(image_path).convert('RGBA')
        img_data = img.tobytes()
        width, height = img.size
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        return tex_id, width, height

    def draw(self, screen_width, screen_height):
        if not self.textures:
            return
        idx = self.current_index % len(self.textures)
        tex_id, w, h = self.textures[idx]
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(0, 0)
        glTexCoord2f(1, 0); glVertex2f(screen_width, 0)
        glTexCoord2f(1, 1); glVertex2f(screen_width, screen_height)
        glTexCoord2f(0, 1); glVertex2f(0, screen_height)
        glEnd()
        glDisable(GL_TEXTURE_2D)

    def next(self):
        if self.textures:
            self.current_index = (self.current_index + 1) % len(self.textures)
            print(f"Fondo cambiado a: {self.current_index}")

    def previous(self):
        if self.textures:
            self.current_index = (self.current_index - 1) % len(self.textures)
            print(f"Fondo cambiado a: {self.current_index}")

class BouncingGIF:
    def __init__(self, gif_path, screen_width, screen_height, on_ready=None, stick_on_collision=False, max_width=None, max_height=None, colision_tipo=None):
        self.frames = []
        self.sizes = []
        self.index = 0
        self.width = 1
        self.height = 1
        self.x = 0
        self.y = 0
        self.dx = random.choice([-5, 5])
        self.dy = random.choice([-5, 5])
        self.ready = False
        self.rotate_angle = 0
        self.rotate_enabled = False
        self._gif_path = gif_path
        self._on_ready = on_ready
        self._pil_frames = []
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.stick_on_collision = stick_on_collision
        self.stuck_to = None  # Referencia a otro GIF si está pegado
        self.max_width = max_width
        self.max_height = max_height
        self.colision_tipo = colision_tipo
        # Si es piolet, siempre rota
        if self.colision_tipo == 'piolet':
            self.rotate_enabled = True
        threading.Thread(target=self._load_gif_pil_frames, daemon=True).start()

    def _load_gif_pil_frames(self):
        try:
            img = Image.open(self._gif_path)
        except Exception as e:
            print(f"Error abriendo imagen {self._gif_path}: {e}")
            return
        try:
            n_frames = getattr(img, 'n_frames', 1)
        except Exception:
            n_frames = 1
        def resize_if_needed(im):
            w, h = im.size
            scale = 1.0
            if self.max_width is not None and w > self.max_width:
                scale = min(scale, self.max_width / w)
            if self.max_height is not None and h > self.max_height:
                scale = min(scale, self.max_height / h)
            if scale < 1.0:
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))
                return im.resize((new_w, new_h), Image.LANCZOS)
            return im
        if n_frames > 1:
            for frame in range(n_frames):
                img.seek(frame)
                frame_img = img.convert('RGBA').copy()
                frame_img = resize_if_needed(frame_img)
                self._pil_frames.append(frame_img)
        else:
            frame_img = img.convert('RGBA').copy()
            frame_img = resize_if_needed(frame_img)
            self._pil_frames.append(frame_img)
        if self._on_ready:
            self._on_ready(self)

    def init_textures(self):
        for frame_img in self._pil_frames:
            tex_id, w, h = GIFManager.load_texture_from_pil(frame_img)
            self.frames.append(tex_id)
            self.sizes.append((w, h))
        self.index = 0
        self.width, self.height = self.sizes[0]
        max_x = max(0, self.screen_width - self.width)
        max_y = max(0, self.screen_height - self.height)

        # Nueva lógica: evitar que los GIFs aparezcan demasiado cerca entre sí
        min_distance = 150  # Distancia mínima en píxeles
        max_attempts = 50
        placed = False
        for _ in range(max_attempts):
            candidate_x = random.randint(0, max_x)
            candidate_y = random.randint(0, max_y)
            too_close = False
            # Buscar otros GIFs activos
            from inspect import currentframe, getouterframes
            # Buscar el GIFManager activo en la pila de llamadas
            gif_manager = None
            for frameinfo in getouterframes(currentframe()):
                local_gm = frameinfo.frame.f_locals.get('self', None)
                if hasattr(local_gm, 'active_gifs'):
                    gif_manager = local_gm
                    break
            if gif_manager:
                all_gifs = [g for glist in gif_manager.active_gifs.values() for g in glist if g is not self and hasattr(g, 'x') and hasattr(g, 'y')]
                for other in all_gifs:
                    dx = (candidate_x + self.width/2) - (other.x + other.width/2)
                    dy = (candidate_y + self.height/2) - (other.y + other.height/2)
                    dist = (dx**2 + dy**2) ** 0.5
                    if dist < min_distance:
                        too_close = True
                        break
            if not too_close:
                self.x = candidate_x
                self.y = candidate_y
                placed = True
                break
        if not placed:
            self.x = random.randint(0, max_x)
            self.y = random.randint(0, max_y)
        self.ready = True
        self._pil_frames = []

    def update(self):
        if not self.ready:
            return
        self.index = (self.index + 1) % len(self.frames)
        self.width, self.height = self.sizes[self.index]
        # Si está pegado a otro, sigue su movimiento
        if self.stuck_to is not None:
            self.x = self.stuck_to.x + self.stuck_to.width
            self.y = self.stuck_to.y
            return
        self.x += self.dx
        self.y += self.dy
        if self.x <= 0 or self.x + self.width >= self.screen_width:
            self.dx *= -1
        if self.y <= 0 or self.y + self.height >= self.screen_height:
            self.dy *= -1
        if self.rotate_enabled:
            self.rotate_angle = (self.rotate_angle + 5) % 360

    def draw(self):
        if not self.ready:
            return
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.frames[self.index])
        glColor4f(1, 1, 1, 1)
        if self.rotate_enabled:
            cx = self.x + self.width / 2
            cy = self.y + self.height / 2
            glPushMatrix()
            glTranslatef(cx, cy, 0)
            glRotatef(self.rotate_angle, 0, 0, 1)
            glTranslatef(-cx, -cy, 0)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(self.x, self.y)
        glTexCoord2f(1, 0); glVertex2f(self.x + self.width, self.y)
        glTexCoord2f(1, 1); glVertex2f(self.x + self.width, self.y + self.height)
        glTexCoord2f(0, 1); glVertex2f(self.x, self.y + self.height)
        glEnd()
        if self.rotate_enabled:
            glPopMatrix()
        glDisable(GL_TEXTURE_2D)

class GIFManager:
    def __init__(self):
        self.active_gifs = defaultdict(list)
        self.explosions = []
    pending_gifs = []
    @staticmethod
    def load_texture_from_pil(img):
        img_data = img.tobytes()
        width, height = img.size
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        return tex_id, width, height

    def add_gif(self, key, gif_path, screen_width, screen_height, rotate_on_ready=False, stick_on_collision=False, max_width=None, max_height=None, colision_tipo=None):
        def on_ready(gif_obj):
            GIFManager.pending_gifs.append(gif_obj)
            self.active_gifs[key].append(gif_obj)
            # Si es piolet, ya rota siempre. Si no, solo rota si se pide (Ctrl)
            if rotate_on_ready and getattr(gif_obj, 'colision_tipo', None) != 'piolet':
                gif_obj.rotate_enabled = True
        BouncingGIF(gif_path, screen_width, screen_height, on_ready=on_ready, stick_on_collision=stick_on_collision, max_width=max_width, max_height=max_height, colision_tipo=colision_tipo)

    def remove_gifs(self, key):
        self.active_gifs[key].clear()

    def update(self):
        # Actualizar todos los GIFs
        all_gifs = [gif for gif_list in self.active_gifs.values() for gif in gif_list]
        # Colisiones solo entre los que tienen stick_on_collision
        for i, gif1 in enumerate(all_gifs):
            if not gif1.stick_on_collision or gif1.stuck_to is not None:
                continue
            for gif2 in all_gifs[i+1:]:
                if not gif2.stick_on_collision or gif2.stuck_to is not None:
                    continue
                # Chequeo de colisión AABB
                if (gif1.x < gif2.x + gif2.width and gif1.x + gif1.width > gif2.x and
                    gif1.y < gif2.y + gif2.height and gif1.y + gif1.height > gif2.y):
                    tipo1 = getattr(gif1, 'colision_tipo', None)
                    tipo2 = getattr(gif2, 'colision_tipo', None)
                    # Sangre sobre cabeza solo si colisiona con piolet
                    if (tipo1 == 'cabeza' and tipo2 == 'piolet'):
                        ex = int(gif1.x + gif1.width // 2 - 32)  # 32 = blood.png ancho/2
                        ey = int(gif1.y + gif1.height // 2 - 32)
                        self.explosions.append(ExplosionEffect(ex, ey, cabeza_gif=gif1))
                    elif (tipo2 == 'cabeza' and tipo1 == 'piolet'):
                        ex = int(gif2.x + gif2.width // 2 - 32)
                        ey = int(gif2.y + gif2.height // 2 - 32)
                        self.explosions.append(ExplosionEffect(ex, ey, cabeza_gif=gif2))
                    # Al colisionar, se pegan: gif2 se pega a gif1
                    gif2.stuck_to = gif1
                    gif2.dx = gif1.dx
                    gif2.dy = gif1.dy
        # Actualizar todos los GIFs
        for gif in all_gifs:
            gif.update()
        # Actualizar explosiones y eliminar las inactivas
        for explosion in self.explosions[:]:
            explosion.update()
            if not explosion.active:
                self.explosions.remove(explosion)

    def draw(self):
        # Dibujar GIFs y, si corresponde, la sangre justo después de la cabeza afectada
        drawn_explosions = set()
        for gif_list in self.active_gifs.values():
            for gif in gif_list:
                gif.draw()
                # Si es cabeza, buscar explosiones que estén centradas sobre ella y dibujarlas justo después
                if getattr(gif, 'colision_tipo', None) == 'cabeza':
                    for i, explosion in enumerate(self.explosions):
                        # Comprobar si la explosión está centrada sobre esta cabeza y no se ha dibujado aún
                        cx = int(gif.x + gif.width // 2 - explosion.width // 2)
                        cy = int(gif.y + gif.height // 2 - explosion.height // 2)
                        if (abs(explosion.x - cx) <= 2 and abs(explosion.y - cy) <= 2 and id(explosion) not in drawn_explosions):
                            explosion.draw()
                            drawn_explosions.add(id(explosion))
        # Dibujar el resto de explosiones (por si hay alguna no asociada a cabeza)
        for explosion in self.explosions:
            if id(explosion) not in drawn_explosions:
                explosion.draw()

    def process_pending(self):
        for gif in GIFManager.pending_gifs[:]:
            if gif._pil_frames:
                gif.init_textures()
                GIFManager.pending_gifs.remove(gif)

class OpenGLApp:
    def __init__(self):
        self.fullscreen = False
        self.screen_width = 800
        self.screen_height = 600
        self.backgrounds = Backgrounds
        self.gif_mapping = Gif_mapping
        self.bg_manager = BackgroundManager(self.backgrounds)
        self.gif_manager = GIFManager()
        # self.current_bg_index eliminado, el fondo se gestiona en BackgroundManager

    def display(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        self.bg_manager.draw(self.screen_width, self.screen_height)
        self.gif_manager.draw()
        glutSwapBuffers()

    def idle(self):
        self.gif_manager.process_pending()
        self.gif_manager.update()
        glutPostRedisplay()
        time.sleep(1/FPS)

    def keyboard(self, key, x, y):
        mods = glutGetModifiers()
        # print(f"Tecla: {key}, mods: {mods}")
        # Shift + tecla: eliminar todos los GIFs de esa tecla
        if (mods & GLUT_ACTIVE_SHIFT):
            key_lower = key.lower()
            if key_lower in self.gif_mapping:
                self.gif_manager.remove_gifs(key_lower)
            return

        # Si Ctrl está activo y la tecla es Ctrl+letra, traducir a la letra
        gif_key = key
        if (mods & GLUT_ACTIVE_CTRL):
            if isinstance(key, bytes) and len(key) == 1 and 1 <= key[0] <= 26:
                gif_key = bytes([key[0] + 96])  # 1->97('a'), 2->98('b'), ...
        
        # Ctrl+letra: crear GIF rotativo (excepto si es piolet, que ya rota siempre)
        if (mods & GLUT_ACTIVE_CTRL) and gif_key in self.gif_mapping:
            gif_info = self.gif_mapping[gif_key]
            gif_path = gif_info['path']
            stick = gif_info.get('stick_on_collision', False)
            max_width = gif_info.get('max_width')
            max_height = gif_info.get('max_height')
            colision_tipo = gif_info.get('colision_tipo')
            if os.path.exists(gif_path):
                self.gif_manager.add_gif(gif_key, gif_path, self.screen_width, self.screen_height, rotate_on_ready=True, stick_on_collision=stick, max_width=max_width, max_height=max_height, colision_tipo=colision_tipo)
            return

        # Tecla normal: añadir un nuevo GIF (sin eliminar los anteriores)
        if gif_key in self.gif_mapping:
            gif_info = self.gif_mapping[gif_key]
            gif_path = gif_info['path']
            stick = gif_info.get('stick_on_collision', False)
            max_width = gif_info.get('max_width')
            max_height = gif_info.get('max_height')
            colision_tipo = gif_info.get('colision_tipo')
            if os.path.exists(gif_path):
                self.gif_manager.add_gif(gif_key, gif_path, self.screen_width, self.screen_height, stick_on_collision=stick, max_width=max_width, max_height=max_height, colision_tipo=colision_tipo)
            return

        # Otras teclas
        match key:
            case b'\x1b': # ESC para salir
                try:
                    glutLeaveMainLoop()
                except Exception:
                    sys.exit()
            case b'\x27': # Flecha derecha
                self.bg_manager.next()
            case b'\x25': # Flecha izquierda
                self.bg_manager.previous()
            case _:
                pass

    def reshape(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, width, height, 0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def run(self):
        glutInit(sys.argv)
        self.screen_width = glutGet(GLUT_SCREEN_WIDTH)
        self.screen_height = glutGet(GLUT_SCREEN_HEIGHT)
        glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_ALPHA | GLUT_DEPTH)
        glutInitWindowSize(self.screen_width, self.screen_height)
        glutInitWindowPosition(0, 0)
        glutCreateWindow(b'Sanches Sesion')
        if self.fullscreen:
            glutFullScreen()
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.bg_manager.load_textures()
        glutDisplayFunc(self.display)
        glutIdleFunc(self.idle)
        glutKeyboardFunc(self.keyboard)
        glutReshapeFunc(self.reshape)
        glutMainLoop()


class ExplosionEffect:
    def __init__(self, x, y, duration_frames=30, image_path='./img/blood.png', cabeza_gif=None):
        self.x = x
        self.y = y
        self.duration = duration_frames
        self.frame = 0
        self.active = True
        self.texture_id = None
        self.width = 64
        self.height = 64
        self.cabeza_gif = cabeza_gif  # Referencia al GIF de tipo cabeza
        try:
            img = Image.open(image_path).convert('RGBA')
            self.width, self.height = img.size
            img_data = img.tobytes()
            self.texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.texture_id)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width, self.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        except Exception as e:
            print(f"Error cargando imagen de explosión: {e}")
            self.active = False

    def update(self):
        self.frame += 1
        if self.cabeza_gif is not None:
            # Seguir la cabeza
            self.x = int(self.cabeza_gif.x + self.cabeza_gif.width // 2 - self.width // 2)
            self.y = int(self.cabeza_gif.y + self.cabeza_gif.height // 2 - self.height // 2)
        if self.frame >= self.duration:
            self.active = False

    def draw(self):
        if not self.active or self.texture_id is None:
            return
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(self.x, self.y)
        glTexCoord2f(1, 0); glVertex2f(self.x + self.width, self.y)
        glTexCoord2f(1, 1); glVertex2f(self.x + self.width, self.y + self.height)
        glTexCoord2f(0, 1); glVertex2f(self.x, self.y + self.height)
        glEnd()
        glDisable(GL_TEXTURE_2D)





if __name__ == '__main__':
    app = OpenGLApp()
    app.run()
