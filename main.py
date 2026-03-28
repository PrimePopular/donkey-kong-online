import os
import random
import pygame
import asyncio
from network import Network

# --- TUNE YOUR SPEED HERE ---
MARIO_SPEED = 11     
MARIO_JUMP = -14     
GRAVITY = 1.5       
BARREL_SPEED = 9   
SPAWN_RATE = 100     
HAMMER_TIME = 600    # Mario keeps the hammer in his "pocket" for ~10 seconds
# ----------------------------

os.environ['SDL_VIDEO_CENTERED'] = '1'
pygame.init()
window_width, window_height = 800, 600 
screen = pygame.display.set_mode([window_width, window_height])
pygame.display.set_caption("Donkey Kong Online")
font = pygame.font.SysFont("Arial", 48, bold=True)
timer = pygame.time.Clock()

def load_img(path, scale):
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, (int(scale[0]), int(scale[1])))
    except:
        surf = pygame.Surface(scale); surf.fill((255, 0, 255)); return surf

sw, sh = window_width // 32, window_height // 32

mario_assets = {
    "standing": load_img('assets/images/mario/standing.png', (2*sw, 2.5*sh)),
    "running":  load_img('assets/images/mario/running.png', (2*sw, 2.5*sh)),
    "climb1":   load_img('assets/images/mario/climbing1.png', (2*sw, 2.5*sh)),
    "climb2":   load_img('assets/images/mario/climbing2.png', (2*sw, 2.5*sh)),
    "h_up":     load_img('assets/images/mario/hammer_overhead.png', (3*sw, 3.5*sh)),
    "h_down":   load_img('assets/images/mario/hammer_stand.png', (3*sw, 3.5*sh))
}
hammer_icon = load_img('assets/images/mario/hammer_stand.png', (1.5*sw, 1.5*sh))
barrel_img = load_img('assets/images/barrels/barrel.png', (2*sw, 2*sh))
dk_frames = [load_img(f'assets/images/dk/dk{i}.png', (5*sw, 5*sh)) for i in [1, 2]]
peach_img = load_img('assets/images/peach/peach1.png', (2*sw, 2.5*sh))

class Hammer(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = hammer_icon
        self.rect = self.image.get_rect(topleft=(x, y))

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width):
        super().__init__()
        self.image = pygame.Surface((width, 15))
        self.image.fill((200, 40, 40)) 
        self.rect = self.image.get_rect(topleft=(x, y))

class Ladder(pygame.sprite.Sprite):
    def __init__(self, x, y, height):
        super().__init__()
        self.image = pygame.Surface((24, height), pygame.SRCALPHA)
        for i in range(0, height, 12):
            pygame.draw.line(self.image, (100, 200, 255), (0, i), (24, i), 3)
        self.rect = self.image.get_rect(topleft=(x, y))

class Barrel(pygame.sprite.Sprite):
    def __init__(self, x, y, dir):
        super().__init__()
        self.image = barrel_img
        self.rect = self.image.get_rect(center=(x, y))
        self.y_vel = 0
        self.speed = BARREL_SPEED * dir

    def update(self, platforms):
        self.y_vel += GRAVITY
        self.rect.y += self.y_vel
        hits = pygame.sprite.spritecollide(self, platforms, False)
        if hits:
            self.rect.bottom = hits[0].rect.top
            self.y_vel = 0
            self.rect.x += self.speed
        if self.rect.right >= window_width or self.rect.left <= 0: self.speed *= -1
        if self.rect.top > window_height: self.kill()

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, is_ghost=False):
        super().__init__()
        self.is_ghost = is_ghost
        self.start_pos = (x, y)
        self.image = mario_assets["standing"]
        if is_ghost: self.image.set_alpha(120)
        self.rect = self.image.get_rect(center=(x, y))
        self.x_change = 0
        self.y_vel = 0
        self.on_ground = False
        self.is_climbing = False
        self.is_swinging = False
        self.has_hammer = 0 
        self.anim_timer = 0

    def reset(self):
        self.rect.center = self.start_pos
        self.y_vel = 0
        self.is_climbing = False
        self.is_swinging = False
        self.has_hammer = 0

    def update(self, platforms, ladders):
        if self.is_ghost: return
        keys = pygame.key.get_pressed()
        on_ladder = pygame.sprite.spritecollide(self, ladders, False)
        
        if self.has_hammer > 0: self.has_hammer -= 1
        
        # Check for Manual Swing (Press X)
        if self.has_hammer > 0 and keys[pygame.K_x]:
            self.is_swinging = True
        else:
            self.is_swinging = False

        if on_ladder and (keys[pygame.K_UP] or keys[pygame.K_DOWN]) and not self.is_swinging:
            self.is_climbing = True
            self.y_vel = 0
        
        if self.is_climbing:
            if keys[pygame.K_UP]: self.rect.y -= 5
            elif keys[pygame.K_DOWN]: self.rect.y += 5
            if not on_ladder: self.is_climbing = False
            self.anim_timer += 1
            self.image = mario_assets["climb1"] if (self.anim_timer // 8) % 2 == 0 else mario_assets["climb2"]
        else:
            self.y_vel += GRAVITY
            self.rect.y += self.y_vel
            hits = pygame.sprite.spritecollide(self, platforms, False)
            if hits and self.y_vel > 0:
                self.rect.bottom = hits[0].rect.top
                self.y_vel = 0
                self.on_ground = True
            else: self.on_ground = False
            
            self.rect.x += self.x_change * MARIO_SPEED
            self.anim_timer += 1

            if self.is_swinging:
                self.image = mario_assets["h_up"] if (self.anim_timer // 5) % 2 == 0 else mario_assets["h_down"]
            elif self.x_change != 0:
                self.image = mario_assets["running"]
            else:
                self.image = mario_assets["standing"]
            
            if self.x_change < 0: self.image = pygame.transform.flip(self.image, True, False)

        self.rect.clamp_ip(screen.get_rect())

async def main():
    net = Network()
    try: await asyncio.wait_for(net.connect(), timeout=2.0)
    except: pass

    player = Player(100, 550)
    ghost_sprite = Player(0, 0, True)
    barrels, platforms, ladders, hammers = pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group()

    layout = [(0,580,800), (0,450,650), (150,320,650), (0,190,500)]
    for x,y,w in layout: platforms.add(Platform(x,y,w))
    lads = [(600,450,130), (160,320,130), (450,190,130)]
    for x,y,h in lads: ladders.add(Ladder(x,y,h))
    
    hammers.add(Hammer(300, 420))
    peach_rect = peach_img.get_rect(topleft=(450, 140))
    game_won, running, frame, dk_idx = False, True, 0, 0

    while running:
        frame += 1
        screen.fill((10, 10, 20))

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT: player.x_change = 1
                if event.key == pygame.K_LEFT: player.x_change = -1
                if (event.key == pygame.K_SPACE or event.key == pygame.K_UP) and player.on_ground and not player.is_climbing:
                    player.y_vel = MARIO_JUMP
            if event.type == pygame.KEYUP:
                if event.key in [pygame.K_LEFT, pygame.K_RIGHT]: player.x_change = 0

        if not game_won:
            if frame % 2 == 0:
                try: await net.send_position(player.rect.x, player.rect.y)
                except: pass

            if frame % SPAWN_RATE == 0:
                dk_idx = 1
                barrels.add(Barrel(70, 150, 1))
            elif frame % SPAWN_RATE == 20: dk_idx = 0
            
            player.update(platforms, ladders)
            barrels.update(platforms)

            if pygame.sprite.spritecollide(player, hammers, True):
                player.has_hammer = HAMMER_TIME

            barrel_hits = pygame.sprite.spritecollide(player, barrels, False)
            if barrel_hits:
                # CRITICAL: Only kill barrels if player is ACTIVELY SWINGING (Holding X)
                if player.is_swinging:
                    for b in barrel_hits: b.kill()
                else:
                    player.reset()

            if player.rect.colliderect(peach_rect): game_won = True

        platforms.draw(screen); ladders.draw(screen); hammers.draw(screen); barrels.draw(screen)
        screen.blit(dk_frames[dk_idx], (20, 95))
        screen.blit(peach_img, peach_rect)

        if net.others:
            for id, pos in net.others.items():
                ghost_sprite.rect.topleft = (pos.get('x',0), pos.get('y',0))
                screen.blit(ghost_sprite.image, ghost_sprite.rect)

        screen.blit(player.image, player.rect)
        
        # UI for Hammer
        if player.has_hammer > 0:
            timer_text = font.render(f"HAMMER: {player.has_hammer // 60}s (Hold X)", True, (255, 255, 255))
            screen.blit(timer_text, (window_width - 350, 20))

        if game_won:
            win_text = font.render("LEVEL CLEAR!", True, (255, 255, 0))
            screen.blit(win_text, (window_width//2 - 150, window_height//2 - 50))

        pygame.display.flip()
        await asyncio.sleep(0); timer.tick(60)
    pygame.quit()

if __name__ == "__main__": asyncio.run(main())
