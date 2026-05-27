import random
import pygame
import sys
import os
import math

# --- Configuration globale initiale ---
pygame.init()
pygame.font.init()

LARG_FENETRE = 1200
HAUT_FENETRE = 720
screen = pygame.display.set_mode((LARG_FENETRE, HAUT_FENETRE))
pygame.display.set_caption("Simulation Écosystème : Renards & Lapins")
clock = pygame.time.Clock()

# --- Palette de Couleurs (Thème Premium Sombre) ---
COLOR_BG = (15, 15, 26)           # Fond général très sombre
COLOR_PANEL = (24, 24, 43)        # Panneau latéral/cartes
COLOR_BTN = (41, 128, 185)        # Bleu interactif
COLOR_BTN_HOVER = (52, 152, 219)  # Bleu survolé
COLOR_BTN_GREEN = (39, 174, 96)   # Vert d'action
COLOR_BTN_GREEN_HOVER = (46, 204, 113)
COLOR_TEXT = (240, 240, 245)
COLOR_TEXT_MUTED = (150, 150, 180)
COLOR_GRID_BG = (20, 36, 28)      # Vert sombre de fond de grille
COLOR_TILE = (39, 97, 61)         # Vert herbe
COLOR_TILE_BORDER = (32, 80, 50)  # Bordure d'herbe
COLOR_LAPIN = (241, 196, 15)      # Jaune lapin brillant
COLOR_RENARD = (231, 76, 60)      # Rouge renard brillant
COLOR_GRAPH_GRID = (35, 35, 55)

# --- Polices ---
try:
    font_large = pygame.font.SysFont("Segoe UI", 36, bold=True)
    font_title = pygame.font.SysFont("Segoe UI", 26, bold=True)
    font_subtitle = pygame.font.SysFont("Segoe UI", 20, bold=True)
    font_ui = pygame.font.SysFont("Segoe UI", 15, bold=False)
    font_ui_bold = pygame.font.SysFont("Segoe UI", 15, bold=True)
    font_energy = pygame.font.SysFont("Segoe UI", 12, bold=True)
except:
    font_large = pygame.font.Font(None, 48)
    font_title = pygame.font.Font(None, 36)
    font_subtitle = pygame.font.Font(None, 28)
    font_ui = pygame.font.Font(None, 18)
    font_ui_bold = pygame.font.Font(None, 18)
    font_energy = pygame.font.Font(None, 14)

# --- Variables de Simulation Modifiables par l'utilisateur ---
initial_nb_lapins = 20
initial_nb_renards = 6
grid_size_taille = 8  # TAILLE

# Constantes algorithmiques d'origine
PROBA_REPRODUCTION_LAPIN = 0.12
ENERGIE_INITIALE_RENARD = 6
ENERGIE_PAR_REPAS = 5
NB_TOURS = 20

# Variables d'état de la simulation
lapins = set()
renards = {}
historique_lapins = []
historique_renards = []
max_historique_lapins = 0
max_historique_renards = 0
tour_actuel = 0

# --- États de la machine à états (FSM) ---
# États : 'WELCOME', 'LOADING', 'SIMULATION', 'SUMMARY'
app_state = 'WELCOME'

# --- Variables pour l'écran de chargement ---
loading_progress = 0.0
loading_messages = [
    "Les lapins se déplacent aléatoirement et cherchent de l'herbe fraîche...",
    "Chaque lapin a 12% de chance de se reproduire à chaque tour de simulation.",
    "Les renards se déplacent et perdent 1 point d'énergie par déplacement.",
    "Manger un lapin redonne 5 points d'énergie au renard prédateur.",
    "Un renard qui atteint 0 point d'énergie meurt instantanément de faim.",
    "L'équilibre des populations dépend des conditions initiales choisies !"
]
current_loading_msg_idx = 0
loading_msg_timer = 0

# --- Assets ---
sprite_rabbit = None
sprite_fox = None
cell_size_px = 75
grid_offset_x = 30
grid_offset_y = 80

def init_simulation():
    global lapins, renards, historique_lapins, historique_renards, tour_actuel, cell_size_px
    global max_historique_lapins, max_historique_renards, sprite_rabbit, sprite_fox
    
    # 1. Ajustement dynamique de la taille de cellule en fonction de la taille de grille choisie
    max_grid_space = 620
    cell_size_px = max_grid_space // grid_size_taille
    
    # Recharge les sprites à la bonne échelle
    sprite_rabbit = load_sprite("assets/rabbit.png", int(cell_size_px * 0.8))
    sprite_fox = load_sprite("assets/fox.png", int(cell_size_px * 0.85))
    
    # 2. Initialisation des agents selon l'algorithme d'origine
    lapins = set()
    while len(lapins) < initial_nb_lapins:
        lapins.add((random.randint(0, grid_size_taille - 1),
                    random.randint(0, grid_size_taille - 1)))

    renards = {}
    while len(renards) < initial_nb_renards:
        pos = (random.randint(0, grid_size_taille - 1),
               random.randint(0, grid_size_taille - 1))
        if pos not in lapins:
            renards[pos] = ENERGIE_INITIALE_RENARD

    # 3. Réinitialiser les statistiques
    historique_lapins = [len(lapins)]
    historique_renards = [len(renards)]
    max_historique_lapins = len(lapins)
    max_historique_renards = len(renards)
    tour_actuel = 0

def load_sprite(path, size):
    if os.path.exists(path):
        try:
            sprite = pygame.image.load(path).convert_alpha()
            return pygame.transform.smoothscale(sprite, (size, size))
        except Exception as e:
            print(f"Erreur de chargement de {path} : {e}")
    # Sprite de secours
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surf, (200, 200, 200), (size//2, size//2), size//2)
    return surf

def voisins(x, y):
    """Retourne les 4 cases adjacentes (haut/bas/gauche/droite) en restant dans la grille (original)."""
    cases = []
    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
        nx, ny = x+dx, y+dy
        if 0 <= nx < grid_size_taille and 0 <= ny < grid_size_taille:
            cases.append((nx, ny))
    return cases

# --- Variables d'animation de la simulation ---
transition_progress = 1.0
duree_transition_frames = 22.0  # Vitesse de transition
anim_lapins = []
anim_renards = []
particles = []

def add_particle(x, y, color, size_range=(3, 7), life=20):
    for _ in range(8):
        particles.append({
            'x': x,
            'y': y,
            'vx': random.uniform(-2.5, 2.5),
            'vy': random.uniform(-2.5, 2.5),
            'color': color,
            'size': random.randint(*size_range),
            'life': random.randint(int(life*0.5), life),
            'max_life': life
        })

def update_particles():
    for p in particles[:]:
        p['x'] += p['vx']
        p['y'] += p['vy']
        p['life'] -= 1
        if p['life'] <= 0:
            particles.remove(p)

def draw_particles(surface):
    for p in particles:
        alpha = int(255 * (p['life'] / p['max_life']))
        s = pygame.Surface((p['size']*2, p['size']*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*p['color'], alpha), (p['size'], p['size']), p['size'])
        surface.blit(s, (p['x'] - p['size'], p['y'] - p['size']))

# --- Simulation Tour Algorithmique (strictement d'origine) ---
def executer_tour():
    global lapins, renards, anim_lapins, anim_renards, tour_actuel
    global max_historique_lapins, max_historique_renards
    
    nouveaux_lapins = set()
    anim_lapins = []
    
    for (x, y) in list(lapins):
        nx, ny = random.choice(voisins(x, y))
        nouveaux_lapins.add((nx, ny))
        anim_lapins.append({
            'from': (x, y),
            'to': (nx, ny),
            'is_new': False,
            'is_eaten': False,
            'alpha': 255
        })
        
        if random.random() < PROBA_REPRODUCTION_LAPIN:
            nouveaux_lapins.add((x, y))
            anim_lapins.append({
                'from': (x, y),
                'to': (x, y),
                'is_new': True,
                'is_eaten': False,
                'alpha': 0
            })
            grid_x = grid_offset_x + x * cell_size_px + cell_size_px // 2
            grid_y = grid_offset_y + y * cell_size_px + cell_size_px // 2
            add_particle(grid_x, grid_y, COLOR_LAPIN, (2, 5), 30)

    nouveaux_renards = {}
    anim_renards = []
    
    for (x, y), energie in list(renards.items()):
        nx, ny = random.choice(voisins(x, y))
        nouvelle_energie = energie - 1
        eaten = False
        
        if (nx, ny) in nouveaux_lapins:
            nouveaux_lapins.discard((nx, ny))
            nouvelle_energie += ENERGIE_PAR_REPAS
            eaten = True
            
            for anim in anim_lapins:
                if anim['to'] == (nx, ny) and not anim['is_new']:
                    anim['is_eaten'] = True
            grid_x = grid_offset_x + nx * cell_size_px + cell_size_px // 2
            grid_y = grid_offset_y + ny * cell_size_px + cell_size_px // 2
            add_particle(grid_x, grid_y, COLOR_RENARD, (3, 6), 25)

        if nouvelle_energie > 0:
            nouveaux_renards[(nx, ny)] = nouvelle_energie
            anim_renards.append({
                'from': (x, y),
                'to': (nx, ny),
                'is_dead': False,
                'energy_start': energie,
                'energy_end': nouvelle_energie
            })
        else:
            anim_renards.append({
                'from': (x, y),
                'to': (nx, ny),
                'is_dead': True,
                'energy_start': energie,
                'energy_end': 0
            })
            grid_x = grid_offset_x + nx * cell_size_px + cell_size_px // 2
            grid_y = grid_offset_y + ny * cell_size_px + cell_size_px // 2
            add_particle(grid_x, grid_y, (100, 100, 100), (2, 4), 20)

    lapins = nouveaux_lapins
    renards = nouveaux_renards
    
    historique_lapins.append(len(lapins))
    historique_renards.append(len(renards))
    
    max_historique_lapins = max(max_historique_lapins, len(lapins))
    max_historique_renards = max(max_historique_renards, len(renards))
    
    tour_actuel += 1

# --- Fonctions Utilitaires UI ---

def draw_button(text, x, y, w, h, bg_color, hover_color, active_state_change=None):
    """Dessine un bouton arrondi premium et retourne si cliqué."""
    mouse_pos = pygame.mouse.get_pos()
    is_hover = x <= mouse_pos[0] <= x + w and y <= mouse_pos[1] <= y + h
    
    curr_color = hover_color if is_hover else bg_color
    pygame.draw.rect(screen, curr_color, (x, y, w, h), border_radius=8)
    
    # Ombre légère
    pygame.draw.rect(screen, (0, 0, 0, 40), (x, y, w, h), width=2, border_radius=8)
    
    text_surf = font_subtitle.render(text, True, COLOR_TEXT)
    text_rect = text_surf.get_rect(center=(x + w//2, y + h//2))
    screen.blit(text_surf, text_rect)
    
    # Clic
    mouse_click = pygame.mouse.get_pressed()
    if is_hover and mouse_click[0]:
        pygame.time.wait(150)  # Eviter double clic
        return True
    return False

# --- ÉCRAN 1 : WELCOME (Accueil & Configuration) ---

def render_welcome_screen():
    global initial_nb_lapins, initial_nb_renards, grid_size_taille, app_state, NB_TOURS
    
    screen.fill(COLOR_BG)
    
    # Fond décoratif (grille de fond futuriste subtile)
    for i in range(0, LARG_FENETRE, 60):
        pygame.draw.line(screen, (22, 22, 38), (i, 0), (i, HAUT_FENETRE))
    for j in range(0, HAUT_FENETRE, 60):
        pygame.draw.line(screen, (22, 22, 38), (0, j), (LARG_FENETRE, j))
        
    # Titre Principal
    title_shadow = font_large.render("SIMULATION DE L'ÉCOSYSTÈME", True, (10, 10, 20))
    screen.blit(title_shadow, (LARG_FENETRE // 2 - title_shadow.get_width() // 2 + 2, 82))
    title_surf = font_large.render("SIMULATION DE L'ÉCOSYSTÈME", True, COLOR_TEXT)
    screen.blit(title_surf, (LARG_FENETRE // 2 - title_surf.get_width() // 2, 80))
    
    sub_surf = font_ui.render("Configurez les populations de départ pour lancer la simulation interactive.", True, COLOR_TEXT_MUTED)
    screen.blit(sub_surf, (LARG_FENETRE // 2 - sub_surf.get_width() // 2, 135))
    
    # Panneau de réglages central
    box_w, box_h = 600, 420
    box_x = LARG_FENETRE // 2 - box_w // 2
    box_y = 175
    pygame.draw.rect(screen, COLOR_PANEL, (box_x, box_y, box_w, box_h), border_radius=15)
    pygame.draw.rect(screen, (40, 40, 65), (box_x, box_y, box_w, box_h), width=2, border_radius=15)
    
    max_animals = grid_size_taille * grid_size_taille

    # Réglage 1 : Lapins de départ
    label_lapins = font_subtitle.render("Lapins de départ :", True, COLOR_TEXT)
    screen.blit(label_lapins, (box_x + 50, box_y + 40))
    
    val_lapins = font_title.render(f"{initial_nb_lapins}", True, COLOR_LAPIN)
    screen.blit(val_lapins, (box_x + box_w - 200, box_y + 35))
    
    if draw_button("-", box_x + box_w - 120, box_y + 35, 40, 35, (40, 40, 60), (60, 60, 80)):
        initial_nb_lapins = max(2, initial_nb_lapins - 2)
    if draw_button("+", box_x + box_w - 70, box_y + 35, 40, 35, (40, 40, 60), (60, 60, 80)):
        if initial_nb_lapins + 2 + initial_nb_renards <= max_animals:
            initial_nb_lapins = min(100, initial_nb_lapins + 2)
        
    # Réglage 2 : Renards de départ
    label_renards = font_subtitle.render("Renards de départ :", True, COLOR_TEXT)
    screen.blit(label_renards, (box_x + 50, box_y + 110))
    
    val_renards = font_title.render(f"{initial_nb_renards}", True, COLOR_RENARD)
    screen.blit(val_renards, (box_x + box_w - 200, box_y + 105))
    
    if draw_button("-", box_x + box_w - 120, box_y + 105, 40, 35, (40, 40, 60), (60, 60, 80)):
        initial_nb_renards = max(1, initial_nb_renards - 1)
    if draw_button("+", box_x + box_w - 70, box_y + 105, 40, 35, (40, 40, 60), (60, 60, 80)):
        if initial_nb_lapins + initial_nb_renards + 1 <= max_animals:
            initial_nb_renards = min(40, initial_nb_renards + 1)
        
    # Réglage 3 : Taille de la Grille (Côté)
    label_taille = font_subtitle.render("Taille de la grille :", True, COLOR_TEXT)
    screen.blit(label_taille, (box_x + 50, box_y + 180))
    
    val_taille = font_title.render(f"{grid_size_taille} x {grid_size_taille}", True, COLOR_TEXT)
    screen.blit(val_taille, (box_x + box_w - 240, box_y + 175))
    
    if draw_button("-", box_x + box_w - 120, box_y + 175, 40, 35, (40, 40, 60), (60, 60, 80)):
        if grid_size_taille > 5:
            grid_size_taille -= 1
            # Ajustement automatique si dépassement de la capacité
            cap = grid_size_taille * grid_size_taille
            while initial_nb_lapins + initial_nb_renards > cap:
                if initial_nb_lapins > 2:
                    initial_nb_lapins -= 1
                elif initial_nb_renards > 1:
                    initial_nb_renards -= 1
                    
    if draw_button("+", box_x + box_w - 70, box_y + 175, 40, 35, (40, 40, 60), (60, 60, 80)):
        grid_size_taille = min(15, grid_size_taille + 1)

    # Réglage 4 : Nombre de Tours
    label_tours = font_subtitle.render("Nombre de tours :", True, COLOR_TEXT)
    screen.blit(label_tours, (box_x + 50, box_y + 250))
    
    val_tours = font_title.render(f"{NB_TOURS}", True, COLOR_TEXT)
    screen.blit(val_tours, (box_x + box_w - 200, box_y + 245))
    
    if draw_button("-", box_x + box_w - 120, box_y + 245, 40, 35, (40, 40, 60), (60, 60, 80)):
        NB_TOURS = max(5, NB_TOURS - 5)
    if draw_button("+", box_x + box_w - 70, box_y + 245, 40, 35, (40, 40, 60), (60, 60, 80)):
        NB_TOURS = min(100, NB_TOURS + 5)
        
    # Indicateur de capacité
    total_animaux = initial_nb_lapins + initial_nb_renards
    occupation_pct = int((total_animaux / max_animals) * 100)
    info_cap = f"Occupation : {total_animaux} / {max_animals} cases ({occupation_pct}%)"
    color_info = COLOR_TEXT_MUTED if occupation_pct < 85 else (230, 126, 34)
    if occupation_pct >= 100:
        color_info = COLOR_RENARD
        
    info_surf = font_ui.render(info_cap, True, color_info)
    screen.blit(info_surf, (box_x + 50, box_y + 305))
        
    # Bouton Lancer
    if draw_button("Lancer la simulation", LARG_FENETRE // 2 - 150, box_y + 345, 300, 50, COLOR_BTN_GREEN, COLOR_BTN_GREEN_HOVER):
        # Initialiser et passer à l'état de chargement
        init_simulation()
        app_state = 'LOADING'

# --- ÉCRAN 2 : LOADING (Chargement avec Explications) ---

def render_loading_screen():
    global loading_progress, app_state, current_loading_msg_idx, loading_msg_timer
    
    screen.fill(COLOR_BG)
    
    # Progression du chargement
    loading_progress += 0.008
    if loading_progress >= 1.0:
        loading_progress = 0.0
        app_state = 'SIMULATION'
        
    # Timer pour le carrousel d'explications
    loading_msg_timer += 1
    if loading_msg_timer > 120:  # Changer toutes les 2 secondes à 60 FPS
        loading_msg_timer = 0
        current_loading_msg_idx = (current_loading_msg_idx + 1) % len(loading_messages)
        
    # Titre "Chargement de la simulation"
    t_surf = font_title.render("Initialisation de l'écosystème...", True, COLOR_TEXT)
    screen.blit(t_surf, (LARG_FENETRE // 2 - t_surf.get_width() // 2, 200))
    
    # Cercle de chargement rotatif
    cx, cy = LARG_FENETRE // 2, 320
    radius = 40
    pygame.draw.circle(screen, (30, 30, 50), (cx, cy), radius, 6)
    
    # Arc de chargement
    angle = int(loading_progress * 360)
    for a in range(angle, angle + 90):
        rad = math.radians(a)
        px = cx + int(math.cos(rad) * radius)
        py = cy + int(math.sin(rad) * radius)
        pygame.draw.circle(screen, COLOR_BTN, (px, py), 4)
        
    # Barre de progression rectiligne
    bar_w, bar_h = 400, 10
    pygame.draw.rect(screen, (30, 30, 50), (LARG_FENETRE // 2 - bar_w // 2, 400, bar_w, bar_h), border_radius=5)
    pygame.draw.rect(screen, COLOR_BTN, (LARG_FENETRE // 2 - bar_w // 2, 400, int(bar_w * loading_progress), bar_h), border_radius=5)
    
    # Explication pédagogique dans une carte arrondie
    card_w, card_h = 700, 100
    card_x = LARG_FENETRE // 2 - card_w // 2
    card_y = 470
    pygame.draw.rect(screen, COLOR_PANEL, (card_x, card_y, card_w, card_h), border_radius=12)
    pygame.draw.rect(screen, COLOR_BTN, (card_x, card_y, card_w, card_h), width=1, border_radius=12)
    
    # Ampoule ou icône d'info
    info_header = font_ui_bold.render("LE SAVIEZ-VOUS ?", True, COLOR_BTN)
    screen.blit(info_header, (card_x + 25, card_y + 20))
    
    msg_surf = font_ui.render(loading_messages[current_loading_msg_idx], True, COLOR_TEXT)
    screen.blit(msg_surf, (card_x + 25, card_y + 50))

# --- ÉCRAN 3 : SIMULATION (Interface Interactive Animée) ---

def draw_grid():
    grid_rect = pygame.Rect(grid_offset_x, grid_offset_y, grid_size_taille * cell_size_px, grid_size_taille * cell_size_px)
    pygame.draw.rect(screen, COLOR_GRID_BG, grid_rect, border_radius=10)
    
    for y in range(grid_size_taille):
        for x in range(grid_size_taille):
            tile_rect = pygame.Rect(
                grid_offset_x + x * cell_size_px + 2,
                grid_offset_y + y * cell_size_px + 2,
                cell_size_px - 4,
                cell_size_px - 4
            )
            pygame.draw.rect(screen, COLOR_TILE, tile_rect, border_radius=6)
            pygame.draw.rect(screen, COLOR_TILE_BORDER, tile_rect, width=1, border_radius=6)

def get_screen_pos(grid_pos):
    x, y = grid_pos
    return (
        grid_offset_x + x * cell_size_px + cell_size_px // 2,
        grid_offset_y + y * cell_size_px + cell_size_px // 2
    )

def draw_agents(p):
    # 1. Dessiner les lapins
    for anim in anim_lapins:
        start_x, start_y = get_screen_pos(anim['from'])
        end_x, end_y = get_screen_pos(anim['to'])
        
        curr_x = start_x + (end_x - start_x) * p
        curr_y = start_y + (end_y - start_y) * p
        
        scale = 1.0
        alpha = 255
        
        if anim['is_new']:
            scale = p
            alpha = int(255 * p)
        elif anim['is_eaten']:
            if p > 0.5:
                scale = (1.0 - p) * 2.0
                alpha = int(255 * (1.0 - p) * 2.0)
        
        if alpha > 0:
            temp_sprite = sprite_rabbit
            if scale != 1.0:
                new_w = max(1, int(sprite_rabbit.get_width() * scale))
                new_h = max(1, int(sprite_rabbit.get_height() * scale))
                temp_sprite = pygame.transform.smoothscale(sprite_rabbit, (new_w, new_h))
            
            rect = temp_sprite.get_rect(center=(curr_x, curr_y))
            if alpha < 255:
                alpha_sprite = temp_sprite.copy()
                alpha_sprite.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
                screen.blit(alpha_sprite, rect.topleft)
            else:
                screen.blit(temp_sprite, rect.topleft)

    # 2. Dessiner les renards
    for anim in anim_renards:
        start_x, start_y = get_screen_pos(anim['from'])
        end_x, end_y = get_screen_pos(anim['to'])
        
        curr_x = start_x + (end_x - start_x) * p
        curr_y = start_y + (end_y - start_y) * p
        
        scale = 1.0
        alpha = 255
        
        if anim['is_dead']:
            if p > 0.5:
                scale = (1.0 - p) * 2.0
                alpha = int(255 * (1.0 - p) * 2.0)
                
        if alpha > 0:
            temp_sprite = sprite_fox
            if scale != 1.0:
                new_w = max(1, int(sprite_fox.get_width() * scale))
                new_h = max(1, int(sprite_fox.get_height() * scale))
                temp_sprite = pygame.transform.smoothscale(sprite_fox, (new_w, new_h))
                
            rect = temp_sprite.get_rect(center=(curr_x, curr_y))
            if alpha < 255:
                alpha_sprite = temp_sprite.copy()
                alpha_sprite.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
                screen.blit(alpha_sprite, rect.topleft)
            else:
                screen.blit(temp_sprite, rect.topleft)
                
            # Dessiner la jauge d'énergie au-dessus
            curr_energy = anim['energy_start'] + (anim['energy_end'] - anim['energy_start']) * p
            energy_text = font_energy.render(str(max(0, int(round(curr_energy)))), True, (255, 255, 100))
            text_rect = energy_text.get_rect(center=(curr_x, curr_y - 25))
            bg_rect = text_rect.inflate(8, 4)
            pygame.draw.rect(screen, (20, 20, 20), bg_rect, border_radius=4)
            screen.blit(energy_text, text_rect)

def draw_stats_panel(p):
    """Dessine le graphique avec tracé animé."""
    panel_x = 680
    panel_y = grid_offset_y
    panel_w = 490
    panel_h = 610
    
    # Fond
    pygame.draw.rect(screen, COLOR_PANEL, (panel_x, panel_y, panel_w, panel_h), border_radius=10)
    
    # Titre du panneau de statistiques
    title_surf = font_subtitle.render("POPULATIONS AU FIL DU TEMPS", True, COLOR_TEXT)
    screen.blit(title_surf, (panel_x + 25, panel_y + 25))
    
    # Zone du graphique
    graph_x = panel_x + 40
    graph_y = panel_y + 100
    graph_w = panel_w - 70
    graph_h = panel_h - 200
    
    pygame.draw.rect(screen, (15, 15, 26), (graph_x, graph_y, graph_w, graph_h))
    
    # Grille du graphique
    for i in range(5):
        ratio = i / 4.0
        gy = graph_y + graph_h - (ratio * graph_h)
        pygame.draw.line(screen, COLOR_GRAPH_GRID, (graph_x, gy), (graph_x + graph_w, gy), 1)
        
        max_pop = max(max_historique_lapins, max_historique_renards, 10)
        y_val = int(ratio * max_pop)
        val_surf = font_ui.render(str(y_val), True, COLOR_TEXT_MUTED)
        screen.blit(val_surf, (graph_x - 30, gy - 8))
        
    # Tracé des courbes
    nb_points = len(historique_lapins)
    if nb_points > 1:
        max_pop = max(max_historique_lapins, max_historique_renards, 10)
        
        # Pour animer les courbes, le dernier segment (entre idx-1 et idx) 
        # grandit linéairement en fonction du progrès d'animation 'p'
        for idx in range(1, nb_points):
            # Coordonnées X des points
            x_start = graph_x + ((idx - 1) / float(NB_TOURS)) * graph_w
            x_end_target = graph_x + (idx / float(NB_TOURS)) * graph_w
            
            # Coordonnées Y
            y_l_start = graph_y + graph_h - (historique_lapins[idx-1] / float(max_pop)) * graph_h
            y_l_end_target = graph_y + graph_h - (historique_lapins[idx] / float(max_pop)) * graph_h
            
            y_r_start = graph_y + graph_h - (historique_renards[idx-1] / float(max_pop)) * graph_h
            y_r_end_target = graph_y + graph_h - (historique_renards[idx] / float(max_pop)) * graph_h
            
            # Si c'est le tout dernier segment (celui du tour en cours de transition)
            if idx == nb_points - 1:
                x_end = x_start + (x_end_target - x_start) * p
                y_l_end = y_l_start + (y_l_end_target - y_l_start) * p
                y_r_end = y_r_start + (y_r_end_target - y_r_start) * p
            else:
                x_end = x_end_target
                y_l_end = y_l_end_target
                y_r_end = y_r_end_target
                
            # Ligne principale
            pygame.draw.line(screen, COLOR_LAPIN, (x_start, y_l_start), (x_end, y_l_end), 3)
            pygame.draw.line(screen, COLOR_RENARD, (x_start, y_r_start), (x_end, y_r_end), 3)
            
            # Points lumineux au bout actuel de la courbe
            if idx == nb_points - 1:
                # Effet de lueur pulsée
                pulse = 1.0 + 0.3 * math.sin(pygame.time.get_ticks() * 0.01)
                pygame.draw.circle(screen, COLOR_LAPIN, (int(x_end), int(y_l_end)), int(5 * pulse))
                pygame.draw.circle(screen, COLOR_RENARD, (int(x_end), int(y_r_end)), int(5 * pulse))

    # Légende et compteurs en bas
    legend_y = panel_y + panel_h - 65
    pygame.draw.circle(screen, COLOR_LAPIN, (panel_x + 50, legend_y), 6)
    lap_text = font_ui_bold.render(f"Lapins : {len(lapins)}", True, COLOR_TEXT)
    screen.blit(lap_text, (panel_x + 65, legend_y - 10))
    
    pygame.draw.circle(screen, COLOR_RENARD, (panel_x + 250, legend_y), 6)
    ren_text = font_ui_bold.render(f"Renards : {len(renards)}", True, COLOR_TEXT)
    screen.blit(ren_text, (panel_x + 265, legend_y - 10))

def draw_header():
    title_text = font_title.render("SIMULATION DE L'ÉCOSYSTÈME", True, COLOR_TEXT)
    screen.blit(title_text, (grid_offset_x, 25))
    
    info_str = f"Tour : {tour_actuel}/{NB_TOURS}   |   🐇 Lapins : {len(lapins)}   |   🦊 Renards : {len(renards)}"
    info_text = font_ui.render(info_str, True, COLOR_TEXT_MUTED)
    screen.blit(info_text, (grid_offset_x, 55))

# --- ÉCRAN 4 : SUMMARY (Résumé & Statistiques) ---

def render_summary_screen():
    global app_state
    
    screen.fill(COLOR_BG)
    
    # Fond
    for i in range(0, LARG_FENETRE, 60):
        pygame.draw.line(screen, (22, 22, 38), (i, 0), (i, HAUT_FENETRE))
    for j in range(0, HAUT_FENETRE, 60):
        pygame.draw.line(screen, (22, 22, 38), (0, j), (LARG_FENETRE, j))
        
    # Titre du Résumé
    t_surf = font_large.render("RÉSUMÉ DE LA SIMULATION", True, COLOR_TEXT)
    screen.blit(t_surf, (LARG_FENETRE // 2 - t_surf.get_width() // 2, 70))
    
    # Carte centrale de résumé
    card_w, card_h = 750, 400
    card_x = LARG_FENETRE // 2 - card_w // 2
    card_y = 150
    pygame.draw.rect(screen, COLOR_PANEL, (card_x, card_y, card_w, card_h), border_radius=15)
    pygame.draw.rect(screen, (50, 50, 75), (card_x, card_y, card_w, card_h), width=2, border_radius=15)
    
    # 1. Verdict Écologique
    verdict = ""
    verdict_color = COLOR_TEXT
    
    if len(lapins) == 0 and len(renards) == 0:
        verdict = "EXTINCTION TOTALE DES ESPÈCES !"
        verdict_color = COLOR_RENARD
    elif len(lapins) == 0:
        verdict = "EXTINCTION DES PROIES (Les renards vont s'éteindre de faim)."
        verdict_color = COLOR_RENARD
    elif len(renards) == 0:
        verdict = "RÈGNE DES LAPINS (Les prédateurs se sont éteints)."
        verdict_color = COLOR_LAPIN
    else:
        verdict = "COEXISTENCE HARMONIEUSE !"
        verdict_color = COLOR_BTN_GREEN_HOVER
        
    v_surf = font_subtitle.render(verdict, True, verdict_color)
    screen.blit(v_surf, (LARG_FENETRE // 2 - v_surf.get_width() // 2, card_y + 35))
    
    # Ligne de séparation
    pygame.draw.line(screen, (40, 40, 60), (card_x + 50, card_y + 85), (card_x + card_w - 50, card_y + 85), 1)
    
    # Colonnes de Statistiques
    col_y = card_y + 110
    
    # Colonne Espèces
    hdr_spec = font_subtitle.render("Espèce", True, COLOR_TEXT_MUTED)
    screen.blit(hdr_spec, (card_x + 100, col_y))
    hdr_start = font_subtitle.render("Départ", True, COLOR_TEXT_MUTED)
    screen.blit(hdr_start, (card_x + 300, col_y))
    hdr_max = font_subtitle.render("Pic Max", True, COLOR_TEXT_MUTED)
    screen.blit(hdr_max, (card_x + 450, col_y))
    hdr_end = font_subtitle.render("Final", True, COLOR_TEXT_MUTED)
    screen.blit(hdr_end, (card_x + 600, col_y))
    
    # Ligne Lapins
    row1_y = col_y + 50
    pygame.draw.circle(screen, COLOR_LAPIN, (card_x + 75, row1_y + 12), 8)
    lbl_lapins = font_title.render("Lapins", True, COLOR_TEXT)
    screen.blit(lbl_lapins, (card_x + 100, row1_y))
    
    val_lap_start = font_title.render(str(initial_nb_lapins), True, COLOR_TEXT)
    screen.blit(val_lap_start, (card_x + 300, row1_y))
    val_lap_max = font_title.render(str(max_historique_lapins), True, COLOR_LAPIN)
    screen.blit(val_lap_max, (card_x + 450, row1_y))
    val_lap_end = font_title.render(str(len(lapins)), True, COLOR_TEXT)
    screen.blit(val_lap_end, (card_x + 600, row1_y))
    
    # Ligne Renards
    row2_y = row1_y + 60
    pygame.draw.circle(screen, COLOR_RENARD, (card_x + 75, row2_y + 12), 8)
    lbl_renards = font_title.render("Renards", True, COLOR_TEXT)
    screen.blit(lbl_renards, (card_x + 100, row2_y))
    
    val_ren_start = font_title.render(str(initial_nb_renards), True, COLOR_TEXT)
    screen.blit(val_ren_start, (card_x + 300, row2_y))
    val_ren_max = font_title.render(str(max_historique_renards), True, COLOR_RENARD)
    screen.blit(val_ren_max, (card_x + 450, row2_y))
    val_ren_end = font_title.render(str(len(renards)), True, COLOR_TEXT)
    screen.blit(val_ren_end, (card_x + 600, row2_y))
    
    # Infos supplémentaires
    extra_y = row2_y + 80
    info_grille = font_ui.render(f"Grille de simulation : {grid_size_taille} x {grid_size_taille} cases", True, COLOR_TEXT_MUTED)
    screen.blit(info_grille, (card_x + 100, extra_y))
    
    info_tours = font_ui.render(f"Tours simulés : {tour_actuel} / {NB_TOURS}", True, COLOR_TEXT_MUTED)
    screen.blit(info_tours, (card_x + 450, extra_y))
    
    # Bouton Recommencer
    if draw_button("Recommencer", LARG_FENETRE // 2 - 120, card_y + card_h + 40, 240, 50, COLOR_BTN, COLOR_BTN_HOVER):
        app_state = 'WELCOME'

# --- Boucle Principale de rendu ---

running = True
simulation_complete = False

# Configuration de l'état initial des animations de départ
anim_lapins = []
anim_renards = []

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
    if app_state == 'WELCOME':
        render_welcome_screen()
        
    elif app_state == 'LOADING':
        render_loading_screen()
        if app_state == 'SIMULATION':
            # S'assurer que les animations initiales sont prêtes
            anim_lapins = []
            anim_renards = []
            for (x, y) in lapins:
                anim_lapins.append({
                    'from': (x, y), 'to': (x, y),
                    'is_new': False, 'is_eaten': False, 'alpha': 255
                })
            for (x, y), e in renards.items():
                anim_renards.append({
                    'from': (x, y), 'to': (x, y),
                    'is_dead': False, 'energy_start': e, 'energy_end': e
                })
            simulation_complete = False
            transition_progress = 1.0
            
    elif app_state == 'SIMULATION':
        # Progression de la transition courante
        if transition_progress < 1.0:
            transition_progress += 1.0 / duree_transition_frames
            if transition_progress >= 1.0:
                transition_progress = 1.0
                
                # Condition d'extinction totale ou fin du nombre de tours
                if (not lapins and not renards) or tour_actuel >= NB_TOURS:
                    simulation_complete = True
                    app_state = 'SUMMARY'
                    
        elif not simulation_complete:
            # Léger délai d'attente pour apprécier l'état statique avant de passer au tour suivant
            pygame.time.wait(350)
            executer_tour()
            transition_progress = 0.0

        # Rendu simulation
        screen.fill(COLOR_BG)
        draw_header()
        draw_grid()
        draw_agents(transition_progress)
        
        # Particules et graphique
        update_particles()
        draw_particles(screen)
        draw_stats_panel(transition_progress)
        
    elif app_state == 'SUMMARY':
        render_summary_screen()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
