import pygame 
import os 
import sys 
import random 
from PIL import Image 

pygame.init() 

# Pantalla completa 
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN) 
screen_width, screen_height = screen.get_size() 
clock = pygame.time.Clock() 
# Fondos (modifica con tus rutas) 
backgrounds = ['background1.jpg', 'background2.jpg'] 
loaded_backgrounds = [pygame.image.load(bg).convert() for bg in backgrounds] 
current_bg_index = 0 
# Teclas y gifs asignados 
gif_mapping = { 
    pygame.K_a: 'espana-spain.gif', 
    pygame.K_b: 'calamardo.gif' 
}

class BouncingGIF: 
    def __init__(self, gif_path): 
        self.frames = self.load_gif_frames(gif_path) 
        self.index = 0 
        self.image = self.frames[self.index] 
        self.rect = self.image.get_rect() 
        self.rect.x = random.randint(0, screen_width - self.rect.width) 
        self.rect.y = random.randint(0, screen_height - self.rect.height) 
        self.dx = 5 
        self.dy = 5 
        
    def load_gif_frames(self, gif_path): 
        frames = [] 
        gif = Image.open(gif_path) 
        for frame in range(gif.n_frames): 
            gif.seek(frame) 
            frame_image = pygame.image.fromstring(gif.tobytes(), gif.size, gif.mode) 
            frames.append(frame_image.convert_alpha()) 
        return frames 
    
    def update(self): 
        self.index = (self.index + 1) % len(self.frames) 
        self.image = self.frames[self.index] 
        self.rect.x += self.dx 
        self.rect.y += self.dy 
        
        if self.rect.left <= 0 or self.rect.right >= screen_width: 
            self.dx *= -1 
        if self.rect.top <= 0 or self.rect.bottom >= screen_height: 
            self.dy *= -1 
    
    def draw(self, surface): 
        surface.blit(self.image, self.rect) 
        
active_gifs = {} 
running = True 

while running: 
    screen.blit(loaded_backgrounds[current_bg_index], (0, 0)) 
    for event in pygame.event.get(): 
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): 
            running = False 
        elif event.type == pygame.KEYDOWN: 
            if event.key == pygame.K_RIGHT: 
                current_bg_index = (current_bg_index + 1) % len(loaded_backgrounds) 
            elif event.key == pygame.K_LEFT: 
                current_bg_index = (current_bg_index - 1) % len(loaded_backgrounds) 
            elif event.key in gif_mapping: 
                gif_path = gif_mapping[event.key] 
                if os.path.exists(gif_path): 
                    active_gifs[event.key] = BouncingGIF(gif_path) 
    
    for gif in active_gifs.values(): 
        gif.update() 
        gif.draw(screen) 
    
    pygame.display.flip() 
    clock.tick(30) 
    
pygame.quit() 
sys.exit()