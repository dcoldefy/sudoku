from flask import Flask, render_template, request, jsonify, send_file
import numpy as np
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import os
import tempfile
from datetime import datetime
import time
import json
import random

app = Flask(__name__)

# Dictionnaire pour stocker les statistiques moyennes par niveau
STATS_FILE = 'generation_stats.json'

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'difficulty_stats': {}}
    return {'difficulty_stats': {}}

def save_stats(stats):
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f)

def update_difficulty_stats(difficulty, timing_stats):
    stats = load_stats()
    diff_key = str(difficulty)
    
    if diff_key not in stats['difficulty_stats']:
        stats['difficulty_stats'][diff_key] = {
            'count': 0,
            'avg_total_time': 0
        }
    
    current_stats = stats['difficulty_stats'][diff_key]
    current_count = current_stats['count']
    current_avg = current_stats['avg_total_time']
    
    # Calculer la nouvelle moyenne
    new_count = current_count + 1
    new_avg = ((current_avg * current_count) + timing_stats['total_time']) / new_count
    
    # Mettre à jour les statistiques
    stats['difficulty_stats'][diff_key] = {
        'count': new_count,
        'avg_total_time': round(new_avg, 2)
    }
    
    save_stats(stats)
    return stats['difficulty_stats'][diff_key]

def get_base_grid():
    """Retourne une grille de Sudoku valide qui servira de base pour les permutations."""
    return [
        [1, 2, 3, 4, 5, 6, 7, 8, 9],
        [4, 5, 6, 7, 8, 9, 1, 2, 3],
        [7, 8, 9, 1, 2, 3, 4, 5, 6],
        [2, 3, 1, 5, 6, 4, 8, 9, 7],
        [5, 6, 4, 8, 9, 7, 2, 3, 1],
        [8, 9, 7, 2, 3, 1, 5, 6, 4],
        [3, 1, 2, 6, 4, 5, 9, 7, 8],
        [6, 4, 5, 9, 7, 8, 3, 1, 2],
        [9, 7, 8, 3, 1, 2, 6, 4, 5]
    ]

def transpose_grid(grid):
    """Transpose la grille (échange lignes et colonnes)."""
    return [[grid[j][i] for j in range(9)] for i in range(9)]

def swap_rows_small(grid):
    """Échange deux lignes dans un même bloc de 3 lignes."""
    grid = [row[:] for row in grid]  # Copie la grille
    block = random.randint(0, 2)  # Choisit un bloc de 3 lignes
    row1, row2 = random.sample(range(block * 3, (block + 1) * 3), 2)  # Choisit 2 lignes dans ce bloc
    grid[row1], grid[row2] = grid[row2], grid[row1]
    return grid

def swap_columns_small(grid):
    """Échange deux colonnes dans un même bloc de 3 colonnes."""
    return transpose_grid(swap_rows_small(transpose_grid(grid)))

def swap_row_blocks(grid):
    """Échange deux blocs de 3 lignes."""
    grid = [row[:] for row in grid]
    block1, block2 = random.sample(range(3), 2)
    for i in range(3):
        grid[block1 * 3 + i], grid[block2 * 3 + i] = grid[block2 * 3 + i], grid[block1 * 3 + i]
    return grid

def swap_column_blocks(grid):
    """Échange deux blocs de 3 colonnes."""
    return transpose_grid(swap_row_blocks(transpose_grid(grid)))

def permute_numbers(grid):
    """Permute les chiffres de 1-9 entre eux."""
    grid = [row[:] for row in grid]
    numbers = list(range(1, 10))
    permutation = list(range(1, 10))
    random.shuffle(permutation)
    
    # Crée un dictionnaire de mapping
    number_map = dict(zip(numbers, permutation))
    
    # Applique la permutation
    for i in range(9):
        for j in range(9):
            grid[i][j] = number_map[grid[i][j]]
    
    return grid

def generate_grid():
    """Génère une nouvelle grille en appliquant des transformations aléatoires."""
    grid = get_base_grid()
    
    # Applique plusieurs transformations aléatoires
    transformations = [
        swap_rows_small,
        swap_columns_small,
        swap_row_blocks,
        swap_column_blocks,
        permute_numbers
    ]
    
    # Applique un nombre aléatoire de transformations (entre 10 et 20)
    for _ in range(random.randint(10, 20)):
        transformation = random.choice(transformations)
        grid = transformation(grid)
    
    return grid

def remove_numbers_for_difficulty(grid, difficulty):
    """Retire des nombres de la grille selon le niveau de difficulté."""
    grid = [row[:] for row in grid]
    difficulty_params = get_difficulty_params(difficulty)
    cells_to_remove = difficulty_params['cells_to_remove']
    
    # Crée une liste de toutes les positions
    positions = [(i, j) for i in range(9) for j in range(9)]
    random.shuffle(positions)
    
    # Retire le nombre spécifié de cellules
    for i, j in positions[:cells_to_remove]:
        grid[i][j] = 0
    
    return grid

def generate_sudoku(difficulty):
    """Génère une grille de Sudoku avec le niveau de difficulté spécifié."""
    # Génère une grille complète
    complete_grid = generate_grid()
    
    # Retire des nombres selon la difficulté
    puzzle = remove_numbers_for_difficulty(complete_grid, difficulty)
    
    return puzzle

def get_difficulty_params(level):
    """
    Retourne les paramètres de difficulté selon les standards courants des sites de Sudoku.
    
    Niveau 1 : Débutant - Beaucoup d'indices, logique simple
    Niveau 2 : Facile - Moins d'indices, mais toujours logique simple
    Niveau 3 : Moyen facile - Introduction de techniques basiques
    Niveau 4 : Moyen - Techniques standards requises
    Niveau 5 : Moyen difficile - Techniques avancées occasionnelles
    Niveau 6 : Difficile - Techniques avancées requises
    Niveau 7 : Très difficile - Techniques expertes nécessaires
    Niveau 8 : Expert - Combinaison de techniques avancées
    Niveau 9 : Extrême - Pour les vrais experts
    """
    difficulty_params = {
        1: {'cells_to_remove': 35, 'max_attempts': 100},  # ~46 indices
        2: {'cells_to_remove': 40, 'max_attempts': 100},  # ~41 indices
        3: {'cells_to_remove': 45, 'max_attempts': 100},  # ~36 indices
        4: {'cells_to_remove': 49, 'max_attempts': 100},  # ~32 indices
        5: {'cells_to_remove': 52, 'max_attempts': 100},  # ~29 indices
        6: {'cells_to_remove': 54, 'max_attempts': 100},  # ~27 indices
        7: {'cells_to_remove': 56, 'max_attempts': 100},  # ~25 indices
        8: {'cells_to_remove': 58, 'max_attempts': 100},  # ~23 indices
        9: {'cells_to_remove': 60, 'max_attempts': 100},  # ~21 indices
    }
    return difficulty_params.get(level, difficulty_params[5])

def get_difficulty_description(level):
    descriptions = {
        1: "Débutant - Beaucoup d'indices, logique simple",
        2: "Facile - Moins d'indices, mais toujours logique simple",
        3: "Moyen facile - Introduction de techniques basiques",
        4: "Moyen - Techniques standards requises",
        5: "Moyen difficile - Techniques avancées occasionnelles",
        6: "Difficile - Techniques avancées requises",
        7: "Très difficile - Techniques expertes nécessaires",
        8: "Expert - Combinaison de techniques avancées",
        9: "Extrême - Pour les vrais experts"
    }
    return descriptions.get(level, descriptions[5])

def create_sudoku_pdf(grids):
    # Créer un fichier temporaire pour le PDF
    pdf_path = os.path.join(tempfile.gettempdir(), f'sudoku_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf')
    
    # Dimensions de la page A4 en mm (portrait)
    width, height = A4
    
    # Créer le PDF
    c = canvas.Canvas(pdf_path, pagesize=A4)
    
    # Définir les marges et la taille des grilles
    margin_left = 20 * mm
    margin_top = 15 * mm
    header_height = 15
    margin_between = 15 * mm
    
    # Calculer la taille optimale des grilles
    usable_width = width - (2 * margin_left)
    usable_height = height - margin_top - header_height - margin_between
    
    # Taille de chaque grille (2 colonnes, 2 rangées)
    grid_size = min(usable_width / 2 - margin_between/2, usable_height / 2 - margin_between/2)
    
    # Position de départ pour chaque grille
    positions = [
        # Première rangée
        (margin_left, height - margin_top - header_height - grid_size),
        (margin_left + grid_size + margin_between, height - margin_top - header_height - grid_size),
        # Deuxième rangée
        (margin_left, height - margin_top - header_height - 2*grid_size - margin_between),
        (margin_left + grid_size + margin_between, height - margin_top - header_height - 2*grid_size - margin_between)
    ]
    
    # Dessiner chaque grille
    for idx, grid in enumerate(grids):
        x, y = positions[idx]
        cell_size = grid_size / 9
        
        # Dessiner les lignes de la grille
        for i in range(10):
            # Ajuster l'épaisseur des lignes
            line_width = 1.5 if i % 3 == 0 else 0.5
            c.setLineWidth(line_width)
            
            # Lignes horizontales
            c.line(x, y - i * cell_size, x + grid_size, y - i * cell_size)
            # Lignes verticales
            c.line(x + i * cell_size, y, x + i * cell_size, y - grid_size)
        
        # Ajouter les nombres
        c.setFont("Helvetica", int(cell_size * 0.6))  
        for i in range(9):
            for j in range(9):
                if grid[i][j] != 0:
                    # Centrer les nombres dans les cellules
                    c.drawString(
                        x + (j + 0.3) * cell_size,
                        y - (i + 0.7) * cell_size,
                        str(grid[i][j])
                    )
    
    # Ajouter un titre et la date
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin_left, height - margin_top + 5, "Grilles de Sudoku")
    
    # Ajouter la date de génération
    current_date = datetime.now().strftime("%d/%m/%Y %H:%M")
    c.setFont("Helvetica", 12)
    c.drawString(margin_left + 150, height - margin_top + 5, f"générée le {current_date}")
    
    # Ajouter le niveau de difficulté et sa description sur une nouvelle ligne
    difficulty_level = request.json.get('difficulty', 1)
    difficulty_desc = get_difficulty_description(difficulty_level)
    c.setFont("Helvetica", 12)
    c.drawString(margin_left, height - margin_top - 8, f"Niveau {difficulty_level} : {difficulty_desc}")
    
    c.save()
    return pdf_path

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    difficulty = int(request.json['difficulty'])
    grids = []
    solutions = []
    generation_times = []
    
    for i in range(4):
        start_time = time.time()
        grid = generate_sudoku(difficulty)
        end_time = time.time()
        generation_time = end_time - start_time
        generation_times.append(generation_time)
        grids.append(grid)
        solutions.append(grid)  # La solution est la même que la grille
    
    # Créer le PDF
    pdf_time_start = time.time()
    pdf_path = create_sudoku_pdf(grids)
    pdf_time = time.time() - pdf_time_start
    
    # Calculer les statistiques
    avg_generation_time = sum(generation_times) / len(generation_times)
    total_time = sum(generation_times) + pdf_time
    
    timing_stats = {
        'average_grid_time': round(avg_generation_time, 2),
        'total_generation_time': round(sum(generation_times), 2),
        'pdf_generation_time': round(pdf_time, 2),
        'total_time': round(total_time, 2),
        'individual_times': [round(t, 2) for t in generation_times]
    }
    
    # Mettre à jour et récupérer les statistiques historiques
    historical_stats = update_difficulty_stats(difficulty, timing_stats)
    timing_stats['historical_avg'] = historical_stats['avg_total_time']
    timing_stats['generation_count'] = historical_stats['count']
    
    return jsonify({
        'grids': grids, 
        'solutions': solutions,
        'pdf_url': f'/download_pdf?path={os.path.basename(pdf_path)}',
        'timing_stats': timing_stats
    })

@app.route('/download_pdf')
def download_pdf():
    pdf_name = request.args.get('path')
    pdf_path = os.path.join(tempfile.gettempdir(), pdf_name)
    return send_file(pdf_path, as_attachment=True, download_name='sudoku.pdf')

@app.route('/get_stats/<difficulty>', methods=['GET'])
def get_stats(difficulty):
    stats = load_stats()
    diff_key = str(difficulty)
    
    if diff_key in stats['difficulty_stats']:
        return jsonify(stats['difficulty_stats'][diff_key])
    else:
        return jsonify({
            'count': 0,
            'avg_total_time': 0
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    
@app.route('/get_stats/<int:id>', methods=['GET'])
def get_stats(id):
    # Votre logique pour récupérer les statistiques
    return jsonify(stats)