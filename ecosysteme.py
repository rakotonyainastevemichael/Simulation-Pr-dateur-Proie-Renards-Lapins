import random                                          # Pour les déplacements et décisions aléatoires
import matplotlib.pyplot as plt                        # Pour afficher la grille animée
import matplotlib.colors as mcolors                   # Pour définir une palette de couleurs personnalisée

TAILLE = 8                                           # Côté de la grille (10x10 = 100 cases)
NB_LAPINS = 20                                       # Nombre de lapins au départ
NB_RENARDS = 6                                   # Nombre de renards au départ
PROBA_REPRODUCTION_LAPIN = 0.12                        # Chance qu'un lapin se reproduise à chaque tour
ENERGIE_INITIALE_RENARD = 6                            # Énergie de départ d'un renard (tours avant de mourir de faim)
ENERGIE_PAR_REPAS = 5                                  # Énergie gagnée quand un renard mange un lapin
NB_TOURS = 20                                         # Durée totale de la simulation

# --- Initialisation des agents ---

lapins = set()                                         # Ensemble des positions (x,y) des lapins (pas de doublon)
while len(lapins) < NB_LAPINS:                         # On tire des positions jusqu'à en avoir assez
    lapins.add((random.randint(0, TAILLE-1),           # Coordonnée x aléatoire entre 0 et 9
                random.randint(0, TAILLE-1)))          # Coordonnée y aléatoire entre 0 et 9

renards = {}                                           # Dictionnaire : position (x,y) → énergie restante
while len(renards) < NB_RENARDS:                       # On place les renards de la même façon
    pos = (random.randint(0, TAILLE-1),                # Tirage de la position x
           random.randint(0, TAILLE-1))                # Tirage de la position y
    if pos not in lapins:                              # On évite de placer un renard sur un lapin dès le début
        renards[pos] = ENERGIE_INITIALE_RENARD         # Le renard commence avec son énergie maximale

def voisins(x, y):
    """Retourne les 4 cases adjacentes (haut/bas/gauche/droite) en restant dans la grille."""
    cases = []                                         # Liste des cases accessibles
    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:        # Les 4 directions cardinales
        nx, ny = x+dx, y+dy                           # Nouvelle position candidate
        if 0 <= nx < TAILLE and 0 <= ny < TAILLE:     # On vérifie qu'on ne sort pas de la grille
            cases.append((nx, ny))                    # On ajoute la case si elle est valide
    return cases                                       # Retourne la liste des voisins valides

def grille_en_image():
    """Convertit l'état des agents en tableau numérique pour matplotlib."""
    img = [[0]*TAILLE for _ in range(TAILLE)]         # 0 = case vide (herbe)
    for (x, y) in lapins:                             # On parcourt chaque lapin
        img[y][x] = 1                                 # 1 = lapin (on note [y][x] car ligne=y, colonne=x)
    for (x, y) in renards:                            # On parcourt chaque renard
        img[y][x] = 2                                 # 2 = renard (écrase le lapin si même case)
    return img                                         # Retourne la grille numérique prête à afficher

# --- Configuration de l'affichage ---

palette = mcolors.ListedColormap(['#2d6a2d', '#e8d44d', '#c0392b'])  # Vert=herbe, Jaune=lapin, Rouge=renard
fig, (ax_grille, ax_stats) = plt.subplots(1, 2, figsize=(12, 5))    # Deux panneaux : grille + courbes
fig.patch.set_facecolor('#1a1a2e')                    # Fond sombre pour toute la fenêtre
plt.ion()                                             # Mode interactif : la fenêtre se met à jour sans bloquer

historique_lapins  = []                               # Liste pour enregistrer le nombre de lapins à chaque tour
historique_renards = []                               # Liste pour enregistrer le nombre de renards à chaque tour

# --- Boucle principale de simulation ---

for tour in range(NB_TOURS):                          # On répète pour chaque tour de simulation

    # 1. Déplacement et reproduction des lapins
    nouveaux_lapins = set()                           # Ensemble temporaire pour les lapins du prochain tour
    for (x, y) in lapins:                            # On traite chaque lapin existant
        nx, ny = random.choice(voisins(x, y))        # Le lapin bouge vers une case voisine au hasard
        nouveaux_lapins.add((nx, ny))                # Il occupe sa nouvelle position
        if random.random() < PROBA_REPRODUCTION_LAPIN:   # Tirage aléatoire : se reproduit-il ?
            nouveaux_lapins.add((x, y))              # Oui : un nouveau lapin naît sur l'ancienne case
    lapins = nouveaux_lapins                          # On remplace l'ancienne génération par la nouvelle

    # 2. Déplacement, chasse et faim des renards
    nouveaux_renards = {}                             # Dictionnaire temporaire pour les renards du prochain tour
    for (x, y), energie in renards.items():          # On traite chaque renard avec son énergie
        nx, ny = random.choice(voisins(x, y))        # Le renard bouge vers une case voisine au hasard
        energie -= 1                                  # Il consomme 1 point d'énergie en se déplaçant
        if (nx, ny) in lapins:                       # Y a-t-il un lapin sur la nouvelle case ?
            lapins.discard((nx, ny))                 # Oui : le lapin est mangé, il disparaît
            energie += ENERGIE_PAR_REPAS             # Le renard récupère de l'énergie
        if energie > 0:                              # Le renard est-il encore en vie (énergie > 0) ?
            nouveaux_renards[(nx, ny)] = energie     # Oui : il survit et occupe sa nouvelle position
    renards = nouveaux_renards                        # On remplace l'ancienne génération par la nouvelle

    # 3. Mise à jour de l'affichage
    historique_lapins.append(len(lapins))            # On note le nombre de lapins ce tour
    historique_renards.append(len(renards))          # On note le nombre de renards ce tour

    ax_grille.clear()                                # On efface la grille précédente
    ax_grille.imshow(grille_en_image(), cmap=palette, vmin=0, vmax=2)  # On affiche la nouvelle grille
    ax_grille.set_title(f'Tour {tour+1}/{NB_TOURS}  |  🐇 {len(lapins)}  🦊 {len(renards)}',
                        color='white', fontsize=13)  # Titre avec compteurs
    ax_grille.axis('off')                            # On masque les axes (pas besoin de coordonnées brutes)

    ax_stats.clear()                                 # On efface le graphique précédent
    ax_stats.plot(historique_lapins,  color='#e8d44d', linewidth=2, label='Lapins')   # Courbe lapins
    ax_stats.plot(historique_renards, color='#c0392b', linewidth=2, label='Renards')  # Courbe renards
    ax_stats.set_facecolor('#16213e')                # Fond sombre pour le graphique
    ax_stats.tick_params(colors='white')             # Couleur blanche pour les chiffres des axes
    ax_stats.legend(facecolor='#1a1a2e', labelcolor='white')  # Légende avec fond sombre
    ax_stats.set_title('Population au fil du temps', color='white')  # Titre du graphique

    plt.tight_layout()                               # Ajuste automatiquement l'espacement entre les panneaux
    plt.pause(0.15)                                  # Pause de 0.15 s entre chaque tour (vitesse de la simu)

    if not lapins and not renards:                   # Si tout le monde est mort, on arrête
        print("Extinction totale !")                 # Message dans le terminal
        break                                        # Sortie de la boucle

plt.ioff()                                           # On désactive le mode interactif
plt.show()                                           # On garde la fenêtre ouverte à la fin
