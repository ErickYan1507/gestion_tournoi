import streamlit as st
import mysql.connector
from mysql.connector import Error
from fpdf import FPDF
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import random
import numpy as np
import time
import json
import base64
from io import BytesIO

# ----------------- Connexion MySQL -----------------
def create_connection():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='tournois_app'
        )
        return conn
    except Error as e:
        st.error(f"Erreur connexion DB : {e}")
        return None

# ----------------- Fonctions d'authentification -----------------
def authenticate_user(username, password):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role, full_name FROM users WHERE username = %s AND password = %s AND is_active = TRUE", (username, password))
        user = cursor.fetchone()
        conn.close()
        return user
    return None

def create_user(username, password, email, full_name, role, tournoi_id=None):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (username, password, email, full_name, role, tournoi_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (username, password, email, full_name, role, tournoi_id))
            conn.commit()
            conn.close()
            return True, "Utilisateur créé avec succès"
        except Error as e:
            conn.close()
            return False, f"Erreur création utilisateur: {e}"
    return False, "Erreur de connexion"

def get_all_users():
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, full_name, role, is_active, created_at FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        conn.close()
        return users
    return []

def update_user(user_id, username, email, full_name, role, is_active, tournoi_id=None):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE users
                SET username=%s, email=%s, full_name=%s, role=%s, is_active=%s, tournoi_id=%s
                WHERE id=%s
            """, (username, email, full_name, role, is_active, tournoi_id, user_id))
            conn.commit()
            conn.close()
            return True, "Utilisateur modifié avec succès"
        except Error as e:
            conn.close()
            return False, f"Erreur modification utilisateur: {e}"
    return False, "Erreur de connexion"

def delete_user(user_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            conn.close()
            return True, "Utilisateur supprimé avec succès"
        except Error as e:
            conn.close()
            return False, f"Erreur suppression utilisateur: {e}"
    return False, "Erreur de connexion"

# ----------------- Fonctions pour visiteurs -----------------
def create_visiteur(nom, email, telephone, preferences=None):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO visiteurs (nom, email, telephone, preferences)
                VALUES (%s, %s, %s, %s)
            """, (nom, email, telephone, preferences))
            conn.commit()
            visiteur_id = cursor.lastrowid
            conn.close()
            return True, "Visiteur enregistré avec succès", visiteur_id
        except Error as e:
            conn.close()
            return False, f"Erreur création visiteur: {e}", None
    return False, "Erreur de connexion", None

def subscribe_visiteur_to_tournoi(visiteur_id, tournoi_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO abonnements_visiteurs (visiteur_id, tournoi_id)
                VALUES (%s, %s)
            """, (visiteur_id, tournoi_id))
            conn.commit()
            conn.close()
            return True, "Abonnement réussi"
        except Error as e:
            conn.close()
            return False, f"Erreur abonnement: {e}"
    return False, "Erreur de connexion"

def get_tournois_public():
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nom, date_debut, date_fin, lieu, description, statut
            FROM tournois
            WHERE statut IN ('en_cours', 'planifié')
            ORDER BY date_debut DESC
        """)
        tournois = cursor.fetchall()
        conn.close()
        return tournois
    return []

def get_classement_public(tournoi_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.nom, g.nom,
            c.matches_joues, c.victories, c.draws, c.losses,
            c.goals_for, c.goals_against, c.points
            FROM classement c
            JOIN equipes e ON c.equipe_id = e.id
            JOIN groupes g ON c.groupe_id = g.id
            WHERE c.tournoi_id = %s
            ORDER BY g.nom, c.points DESC, (c.goals_for - c.goals_against) DESC
        """, (tournoi_id,))
        classement = cursor.fetchall()
        conn.close()
        return classement
    return []

def get_prochains_matchs(tournoi_id, limit=10):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e1.nom, e2.nom, m.date_match, m.lieu, g.nom, m.phase
            FROM matchs m
            JOIN equipes e1 ON m.equipe1_id = e1.id
            JOIN equipes e2 ON m.equipe2_id = e2.id
            LEFT JOIN groupes g ON m.groupe_id = g.id
            WHERE m.tournoi_id = %s AND m.date_match > NOW()
            ORDER BY m.date_match ASC
            LIMIT %s
        """, (tournoi_id, limit))
        matchs = cursor.fetchall()
        conn.close()
        return matchs
    return []

# ----------------- CRUD Tournoi -----------------
def get_tournois():
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nom, date_creation, format_finales, equipes_par_groupe, equipes_qualifiees FROM tournois ORDER BY date_creation DESC")
        res = cursor.fetchall()
        conn.close()
        return res
    return []

def creer_tournoi(nom, format_finales, eq_pg, eq_qual):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tournois (nom, format_finales, equipes_par_groupe, equipes_qualifiees, date_creation)
            VALUES (%s,%s,%s,%s,NOW())
        """, (nom, format_finales, eq_pg, eq_qual))
        conn.commit()
        tid = cursor.lastrowid
        conn.close()
        return tid
    return None

def get_tournoi_details(tournoi_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tournois WHERE id = %s", (tournoi_id,))
        tournoi = cursor.fetchone()
        conn.close()
        return tournoi
    return None

# ----------------- CRUD Équipes -----------------
def get_equipes(tournoi_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nom, groupe, numero FROM equipes WHERE tournoi_id=%s", (tournoi_id,))
        res = cursor.fetchall()
        conn.close()
        return res
    return []

def count_equipes(tournoi_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM equipes WHERE tournoi_id = %s", (tournoi_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    return 0

def ajouter_equipes(tournoi_id, eq_list):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        for nom in eq_list:
            cursor.execute("INSERT INTO equipes (nom, tournoi_id) VALUES (%s,%s)", (nom, tournoi_id))
        conn.commit()
        conn.close()
        return True
    return False

def modifier_equipe(equipe_id, nouveau_nom):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE equipes SET nom=%s WHERE id=%s", (nouveau_nom, equipe_id))
        conn.commit()
        conn.close()
        return True
    return False

def supprimer_equipe(equipe_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM equipes WHERE id=%s", (equipe_id,))
        conn.commit()
        conn.close()
        return True
    return False

# ----------------- CRUD Droits de match -----------------
def get_droits_match(tournoi_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT dm.id, e.nom, dm.montant, dm.paye, dm.date_paiement, dm.date_limite
            FROM droits_match dm
            JOIN equipes e ON dm.equipe_id = e.id
            WHERE dm.tournoi_id = %s
        """, (tournoi_id,))
        res = cursor.fetchall()
        conn.close()
        return res
    return []

def set_droit_match(tournoi_id, equipe_id, montant, date_limite):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO droits_match (tournoi_id, equipe_id, montant, date_limite)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE montant=%s, date_limite=%s
        """, (tournoi_id, equipe_id, montant, date_limite, montant, date_limite))
        conn.commit()
        conn.close()
        return True
    return False

def payer_droit_match(droit_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE droits_match 
            SET paye=TRUE, date_paiement=NOW() 
            WHERE id=%s
        """, (droit_id,))
        conn.commit()
        conn.close()
        return True
    return False

def verifier_equipe_eligible(equipe_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT paye, date_limite
                FROM droits_match 
                WHERE equipe_id = %s
            """, (equipe_id,))
            result = cursor.fetchone()
            
            if not result:
                print(f"Aucun droit trouvé pour l'équipe ID {equipe_id}")
                return False
                
            paye, date_limite = result
            
            # Si date_limite est None, considérer comme valide
            if date_limite is None:
                print(f"Équipe {equipe_id}: paye={paye}, date_limite=None → Consideré valide")
                return bool(paye)
            
            # Vérifier la date si elle existe
            from datetime import date
            date_ok = date_limite >= date.today()
            
            print(f"Équipe {equipe_id}: paye={paye}, date_limite={date_limite}, date_ok={date_ok}")
            
            return bool(paye) and date_ok
            
        except Error as e:
            print(f"Erreur vérification éligibilité: {e}")
            return False
        finally:
            conn.close()
    return False

def debug_droits_equipes(tournoi_id):
    """Affiche le statut détaillé de toutes les équipes"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.id, e.nom, 
                   dm.paye, dm.date_limite, dm.date_paiement,
                   dm.date_limite < NOW() as date_depassee,
                   (dm.paye = TRUE AND dm.date_limite >= NOW()) as eligible
            FROM equipes e
            LEFT JOIN droits_match dm ON e.id = dm.equipe_id
            WHERE e.tournoi_id = %s
        """, (tournoi_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        st.write("### Debug: Statut des droits")
        for row in results:
            st.write(f"**{row[1]}** (ID: {row[0]}): "
                   f"Payé={row[2]}, Date limite={row[3]}, "
                   f"Date dépassée={row[5]}, Eligible={row[6]}")

# ----------------- CRUD Joueurs -----------------
def get_joueurs(equipe_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nom, numero, poste 
            FROM joueurs 
            WHERE equipe_id=%s 
            ORDER BY numero
        """, (equipe_id,))
        res = cursor.fetchall()
        conn.close()
        return res
    return []

def ajouter_joueur(equipe_id, nom, numero, poste):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        # Vérifier si le numéro est déjà utilisé dans l'équipe
        cursor.execute("SELECT id FROM joueurs WHERE equipe_id=%s AND numero=%s", (equipe_id, numero))
        if cursor.fetchone():
            conn.close()
            return False, "Numéro déjà utilisé dans cette équipe"
        
        # Vérifier la limite de 30 joueurs
        cursor.execute("SELECT COUNT(*) FROM joueurs WHERE equipe_id=%s", (equipe_id,))
        if cursor.fetchone()[0] >= 30:
            conn.close()
            return False, "Limite de 30 joueurs atteinte"
        
        cursor.execute("""
            INSERT INTO joueurs (equipe_id, nom, numero, poste)
            VALUES (%s, %s, %s, %s)
        """, (equipe_id, nom, numero, poste))
        conn.commit()
        conn.close()
        return True, "Joueur ajouté avec succès"
    return False, "Erreur de connexion"

def modifier_joueur(joueur_id, nom, numero, poste):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE joueurs 
            SET nom=%s, numero=%s, poste=%s 
            WHERE id=%s
        """, (nom, numero, poste, joueur_id))
        conn.commit()
        conn.close()
        return True
    return False

def supprimer_joueur(joueur_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM joueurs WHERE id=%s", (joueur_id,))
        conn.commit()
        conn.close()
        return True
    return False

# ----------------- Statistiques Joueurs -----------------
def get_stats_joueur(joueur_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(buts), SUM(passes_decisives), SUM(cartons_jaunes), 
                   SUM(cartons_rouges), COUNT(CASE WHEN homme_du_match THEN 1 END)
            FROM stats_joueurs 
            WHERE joueur_id=%s
        """, (joueur_id,))
        stats = cursor.fetchone()
        conn.close()
        return {
            'buts': stats[0] or 0,
            'passes': stats[1] or 0,
            'jaunes': stats[2] or 0,
            'rouges': stats[3] or 0,
            'hommes_du_match': stats[4] or 0
        }
    return {}

def enregistrer_stats_joueur(match_id, joueur_id, buts=0, passes=0, jaunes=0, rouges=0, homme_du_match=False):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO stats_joueurs (match_id, joueur_id, buts, passes_decisives, 
                                     cartons_jaunes, cartons_rouges, homme_du_match)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            buts=buts+VALUES(buts), 
            passes_decisives=passes_decisives+VALUES(passes_decisives),
            cartons_jaunes=cartons_jaunes+VALUES(cartons_jaunes),
            cartons_rouges=cartons_rouges+VALUES(cartons_rouges),
            homme_du_match=VALUES(homme_du_match)
        """, (match_id, joueur_id, buts, passes, jaunes, rouges, homme_du_match))
        conn.commit()
        conn.close()
        return True
    return False

# ----------------- Trophées -----------------
def get_meilleurs_buteurs(tournoi_id, limit=5):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT j.nom, e.nom as equipe, SUM(sj.buts) as buts
            FROM stats_joueurs sj
            JOIN joueurs j ON sj.joueur_id = j.id
            JOIN equipes e ON j.equipe_id = e.id
            JOIN matchs m ON sj.match_id = m.id
            WHERE m.tournoi_id = %s
            GROUP BY j.id
            ORDER BY buts DESC
            LIMIT %s
        """, (tournoi_id, limit))
        result = cursor.fetchall()
        conn.close()
        return result
    return []

def get_meilleurs_joueurs(tournoi_id, limit=5):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT j.nom, e.nom as equipe, 
                   COUNT(CASE WHEN sj.homme_du_match THEN 1 END) as hdm_count,
                   SUM(sj.buts) + SUM(sj.passes_decisives) as points
            FROM stats_joueurs sj
            JOIN joueurs j ON sj.joueur_id = j.id
            JOIN equipes e ON j.equipe_id = e.id
            JOIN matchs m ON sj.match_id = m.id
            WHERE m.tournoi_id = %s
            GROUP BY j.id
                        ORDER BY hdm_count DESC, points DESC
            LIMIT %s
        """, (tournoi_id, limit))
        result = cursor.fetchall()
        conn.close()
        return result
    return []

# ----------------- Groupes -----------------
def creer_groupes(tournoi_id, noms_groupes):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        for nom in noms_groupes:
            cursor.execute("INSERT INTO groupes (nom, tournoi_id) VALUES (%s, %s)", (nom, tournoi_id))
        conn.commit()
        conn.close()
        return True
    return False

def get_groupes(tournoi_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nom FROM groupes WHERE tournoi_id = %s", (tournoi_id,))
        groupes = cursor.fetchall()
        conn.close()
        return groupes
    return []

# ----------------- Matchs et Scores -----------------
def get_matchs(tournoi_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.id, e1.nom, e2.nom, g.nom, m.date_match, m.score1, m.score2, m.phase
            FROM matchs m
            JOIN equipes e1 ON m.equipe1_id=e1.id
            JOIN equipes e2 ON m.equipe2_id=e2.id
            LEFT JOIN groupes g ON m.groupe_id=g.id
            WHERE m.tournoi_id=%s
            ORDER BY m.date_match
        """, (tournoi_id,))
        res = cursor.fetchall()
        conn.close()
        return res
    return []

def get_matchs_by_groupe(tournoi_id, groupe_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.id, e1.nom, e2.nom, m.date_match, m.score1, m.score2
            FROM matchs m
            JOIN equipes e1 ON m.equipe1_id=e1.id
            JOIN equipes e2 ON m.equipe2_id=e2.id
            WHERE m.tournoi_id=%s AND m.groupe_id=%s
            ORDER BY m.date_match
        """, (tournoi_id, groupe_id))
        res = cursor.fetchall()
        conn.close()
        return res
    return []

def creer_match(tournoi_id, equipe1_id, equipe2_id, groupe_id, date_match, phase="Phase de groupes"):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO matchs (tournoi_id, equipe1_id, equipe2_id, groupe_id, date_match, phase)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (tournoi_id, equipe1_id, equipe2_id, groupe_id, date_match, phase))
        conn.commit()
        conn.close()
        return True
    return False

def enregistrer_score(match_id, score1, score2):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE matchs
            SET score1=%s, score2=%s, statut='terminé'
            WHERE id=%s
        """, (score1, score2, match_id))
        conn.commit()
        conn.close()
        return True
    return False

# ----------------- Classement -----------------
def get_classement(tournoi_id, groupe_id=None):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        if groupe_id:
            cursor.execute("""
                SELECT e.nom, c.matches_joues, c.victories, c.draws, c.losses,
                c.goals_for, c.goals_against, c.points
                FROM classement c
                JOIN equipes e ON c.equipe_id = e.id
                WHERE c.tournoi_id = %s AND c.groupe_id = %s
                ORDER BY c.points DESC, (c.goals_for - c.goals_against) DESC
            """, (tournoi_id, groupe_id))
        else:
            cursor.execute("""
                SELECT e.nom, g.nom, c.matches_joues, c.victories, c.draws, c.losses,
                c.goals_for, c.goals_against, c.points
                FROM classement c
                JOIN equipes e ON c.equipe_id = e.id
                JOIN groupes g ON c.groupe_id = g.id
                WHERE c.tournoi_id = %s
                ORDER BY g.nom, c.points DESC, (c.goals_for - c.goals_against) DESC
            """, (tournoi_id,))
        classement = cursor.fetchall()
        conn.close()
        return classement
    return []

def mettre_a_jour_classement(tournoi_id, equipe_id, groupe_id, victoire, nul, defaite, buts_pour, buts_contre):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        # Vérifier si l'équipe existe déjà dans le classement
        cursor.execute("""
            SELECT id FROM classement
            WHERE tournoi_id=%s AND equipe_id=%s AND groupe_id=%s
        """, (tournoi_id, equipe_id, groupe_id))
        existing = cursor.fetchone()
        if existing:
            # Mettre à jour les statistiques existantes
            cursor.execute("""
                UPDATE classement
                SET matches_joues=matches_joues+1,
                victories=victories+%s,
                draws=draws+%s,
                losses=losses+%s,
                goals_for=goals_for+%s,
                goals_against=goals_against+%s,
                points=points+%s
                WHERE id=%s
            """, (victoire, nul, defaite, buts_pour, buts_contre, victoire*3 + nul, existing[0]))
        else:
            # Créer une nouvelle entrée
            cursor.execute("""
                INSERT INTO classement (tournoi_id, equipe_id, groupe_id, matches_joues,
                victories, draws, losses, goals_for, goals_against, points)
                VALUES (%s, %s, %s, 1, %s, %s, %s, %s, %s, %s)
            """, (tournoi_id, equipe_id, groupe_id, victoire, nul, defaite, buts_pour, buts_contre, victoire*3 + nul))
        conn.commit()
        conn.close()
        return True
    return False

# ----------------- Gestion des suspensions -----------------
def get_suspensions_joueur(joueur_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.matchs_suspendus, s.raison, s.date_suspension, s.date_fin_suspension
            FROM suspensions s
            WHERE s.joueur_id = %s AND (s.date_fin_suspension IS NULL OR s.date_fin_suspension > CURDATE())
        """, (joueur_id,))
        suspensions = cursor.fetchall()
        conn.close()
        return suspensions
    return []

def ajouter_suspension(joueur_id, matchs_suspendus, raison, date_fin_suspension=None):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO suspensions (joueur_id, matchs_suspendus, raison, date_fin_suspension)
            VALUES (%s, %s, %s, %s)
        """, (joueur_id, matchs_suspendus, raison, date_fin_suspension))
        conn.commit()
        conn.close()
        return True
    return False

def get_cartons_joueur(joueur_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.type, c.minute, c.raison, m.date_match, e1.nom, e2.nom
            FROM cartons c
            JOIN matchs m ON c.match_id = m.id
            JOIN equipes e1 ON m.equipe1_id = e1.id
            JOIN equipes e2 ON m.equipe2_id = e2.id
            WHERE c.joueur_id = %s
            ORDER BY m.date_match DESC
        """, (joueur_id,))
        cartons = cursor.fetchall()
        conn.close()
        return cartons
    return []

def ajouter_carton(joueur_id, match_id, type_carton, minute, raison):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cartons (joueur_id, match_id, type, minute, raison)
            VALUES (%s, %s, %s, %s, %s)
        """, (joueur_id, match_id, type_carton, minute, raison))
        conn.commit()
        conn.close()
        return True
    return False

# ----------------- Phases finales -----------------
def generer_phases_finales(tournoi_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        
        # Récupérer les équipes qualifiées (top 2 de chaque groupe)
        cursor.execute("""
            SELECT e.id, e.nom, g.nom as groupe_nom
            FROM classement c
            JOIN equipes e ON c.equipe_id = e.id
            JOIN groupes g ON c.groupe_id = g.id
            WHERE c.tournoi_id = %s
            ORDER BY g.nom, c.points DESC, (c.goals_for - c.goals_against) DESC
        """, (tournoi_id,))
        
        equipes_par_groupe = {}
        for equipe in cursor.fetchall():
            groupe_nom = equipe[2]
            if groupe_nom not in equipes_par_groupe:
                equipes_par_groupe[groupe_nom] = []
            if len(equipes_par_groupe[groupe_nom]) < 2:  # Top 2 de chaque groupe
                equipes_par_groupe[groupe_nom].append((equipe[0], equipe[1]))
        
        # Organiser les matchs des phases finales
        equipes_qualifiees = []
        for groupe, equipes in equipes_par_groupe.items():
            equipes_qualifiees.extend(equipes)
        
        # Mélanger les équipes pour le tirage
        random.shuffle(equipes_qualifiees)
        
        # Créer les matchs des huitièmes de finale
        date_match = datetime.now() + timedelta(days=7)
        for i in range(0, len(equipes_qualifiees), 2):
            if i + 1 < len(equipes_qualifiees):
                equipe1_id, equipe1_nom = equipes_qualifiees[i]
                equipe2_id, equipe2_nom = equipes_qualifiees[i + 1]
                
                cursor.execute("""
                    INSERT INTO phases_finales 
                    (tournoi_id, niveau, equipe1_id, equipe2_id, date_match, statut)
                    VALUES (%s, 'Huitième', %s, %s, %s, 'planifié')
                """, (tournoi_id, equipe1_id, equipe2_id, date_match))
                
                date_match += timedelta(hours=2)
        
        conn.commit()
        conn.close()
        return True
    return False

def get_phases_finales(tournoi_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pf.id, pf.niveau, e1.nom, e2.nom, pf.score1, pf.score2, 
                   pf.date_match, pf.statut, g.nom as gagnant
            FROM phases_finales pf
            LEFT JOIN equipes e1 ON pf.equipe1_id = e1.id
            LEFT JOIN equipes e2 ON pf.equipe2_id = e2.id
            LEFT JOIN equipes g ON pf.gagnant_id = g.id
            WHERE pf.tournoi_id = %s
            ORDER BY 
                CASE pf.niveau
                    WHEN 'Huitième' THEN 1
                    WHEN 'Quart' THEN 2
                    WHEN 'Demi' THEN 3
                    WHEN 'Finale' THEN 4
                    WHEN 'Petite finale' THEN 5
                END,
                pf.date_match
        """, (tournoi_id,))
        phases = cursor.fetchall()
        conn.close()
        return phases
    return []

def enregistrer_score_phase_finale(match_id, score1, score2, gagnant_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE phases_finales
            SET score1=%s, score2=%s, gagnant_id=%s, statut='terminé'
            WHERE id=%s
        """, (score1, score2, gagnant_id, match_id))
        conn.commit()
        conn.close()
        return True
    return False

# ----------------- Génération PDF -----------------
def generer_fiche_equipe_pdf(equipe_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        # Récupérer les infos de l'équipe
        cursor.execute("SELECT nom, tournoi_id FROM equipes WHERE id=%s", (equipe_id,))
        equipe = cursor.fetchone()
        # Récupérer les joueurs
        cursor.execute("SELECT nom, numero, poste FROM joueurs WHERE equipe_id=%s ORDER BY numero", (equipe_id,))
        joueurs = cursor.fetchall()
        conn.close()

        # Créer le PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, f"Fiche d'équipe: {equipe[0]}", 0, 1, 'C')
        pdf.ln(10)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, "Liste des joueurs:", 0, 1)
        pdf.ln(5)

        # En-tête du tableau
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(20, 10, "Numéro", 1, 0, 'C', True)
        pdf.cell(80, 10, "Nom", 1, 0, 'C', True)
        pdf.cell(50, 10, "Poste", 1, 1, 'C', True)

        # Données des joueurs
        for joueur in joueurs:
            pdf.cell(20, 10, str(joueur[1]), 1, 0, 'C')
            pdf.cell(80, 10, joueur[0], 1, 0)
            pdf.cell(50, 10, joueur[2], 1, 1)
        return pdf.output(dest='S').encode('latin1')
    return None

def generer_calendrier_pdf(tournoi_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        # Récupérer les infos du tournoi
        cursor.execute("SELECT nom, date_debut, date_fin, lieu FROM tournois WHERE id=%s", (tournoi_id,))
        tournoi = cursor.fetchone()
        
        # Récupérer les matchs
        cursor.execute("""
            SELECT e1.nom, e2.nom, m.date_match, m.lieu, g.nom, m.phase
            FROM matchs m
            JOIN equipes e1 ON m.equipe1_id = e1.id
            JOIN equipes e2 ON m.equipe2_id = e2.id
            LEFT JOIN groupes g ON m.groupe_id = g.id
            WHERE m.tournoi_id = %s
            ORDER BY m.date_match
        """, (tournoi_id,))
        matchs = cursor.fetchall()
        conn.close()

        # Créer le PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, f"Calendrier du tournoi: {tournoi[0]}", 0, 1, 'C')
        pdf.ln(5)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, f"Dates: {tournoi[1]} au {tournoi[2]} - Lieu: {tournoi[3]}", 0, 1)
        pdf.ln(10)

        # En-tête du tableau
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(40, 10, "Date/Heure", 1, 0, 'C', True)
        pdf.cell(60, 10, "Équipe 1", 1, 0, 'C', True)
        pdf.cell(60, 10, "Équipe 2", 1, 0, 'C', True)
        pdf.cell(30, 10, "Lieu", 1, 1, 'C', True)

        # Données des matchs
        for match in matchs:
            date_str = match[2].strftime("%d/%m/%Y %H:%M") if match[2] else "À définir"
            pdf.cell(40, 10, date_str, 1, 0)
            pdf.cell(60, 10, match[0], 1, 0)
            pdf.cell(60, 10, match[1], 1, 0)
            pdf.cell(30, 10, match[3] or "Principal", 1, 1)
        
        return pdf.output(dest='S').encode('latin1')
    return None

# ----------------- Tirage automatique -----------------
def tirage_groupes(tournoi_id):
    eqs = get_equipes(tournoi_id)
    if not eqs:
        return []
    
    # Debug: afficher toutes les équipes et leur statut
    for eq in eqs:
        eligible = verifier_equipe_eligible(eq[0])
        print(f"Équipe {eq[1]} (ID: {eq[0]}): Eligible = {eligible}")
    
    # Vérifier que toutes les équipes ont payé leurs droits
    equipes_non_eligibles = []
    for eq in eqs:
        if not verifier_equipe_eligible(eq[0]):
            equipes_non_eligibles.append(eq[1])
    
    if equipes_non_eligibles:
        st.error(f"Équipes non éligibles (droit non payé): {', '.join(equipes_non_eligibles)}")
        return []
    
    # Récupérer la configuration du tournoi
    conn = create_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    cursor.execute("SELECT equipes_par_groupe FROM tournois WHERE id=%s", (tournoi_id,))
    result = cursor.fetchone()
    equipes_par_groupe = result[0] if result else 4
    
    # Animation du tirage au sort
    st.write("🎲 Tirage au sort en cours...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(15):
        progress_bar.progress((i + 1) / 15)
        status_text.text(f"Tirage en cours... {15-i} secondes")
        time.sleep(1)
    
    status_text.text("Tirage terminé!")
    
    # Mélanger les équipes
    random.shuffle(eqs)
    
    # Créer les groupes (A, B, C, ...)
    nb_groupes = (len(eqs) + equipes_par_groupe - 1) // equipes_par_groupe
    groupes = [f"Groupe {chr(65+i)}" for i in range(nb_groupes)]
    
    # Créer les groupes dans la base
    for nom_groupe in groupes:
        cursor.execute("INSERT IGNORE INTO groupes (nom, tournoi_id) VALUES (%s, %s)", (nom_groupe, tournoi_id))
    
    # Assigner les équipes aux groupes avec numéros aléatoires
    for i, e in enumerate(eqs):
        groupe = groupes[i % len(groupes)]
        # Récupérer l'ID du groupe
        cursor.execute("SELECT id FROM groupes WHERE nom=%s AND tournoi_id=%s", (groupe, tournoi_id))
        groupe_id = cursor.fetchone()[0]
        
        # Assigner un numéro aléatoire entre 1 et 99
        numero_equipe = random.randint(1, 99)
        cursor.execute("UPDATE equipes SET groupe=%s, numero=%s WHERE id=%s", 
                      (groupe, numero_equipe, e[0]))
    
    conn.commit()
    conn.close()
    
    # Afficher le résultat du tirage
    st.success("Tirage terminé avec succès!")
    st.balloons()
    
    return groupes

# ----------------- Génération automatique des matchs -----------------
def generer_matchs_groupes(tournoi_id):
    eqs = get_equipes(tournoi_id)
    if not eqs:
        return False
    
    # Récupérer les groupes
    groupes = {}
    for eq in eqs:
        if eq[2] not in groupes:
            groupes[eq[2]] = []
        groupes[eq[2]].append(eq[0])
    
    # Créer les matchs pour chaque groupe (toutes les équipes se rencontrent)
    conn = create_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    date_match = datetime.now() + timedelta(days=1)  # Commencer demain
    
    for nom_groupe, equipes_ids in groupes.items():
        # Récupérer l'ID du groupe
        cursor.execute("SELECT id FROM groupes WHERE nom=%s AND tournoi_id=%s", (nom_groupe, tournoi_id))
        groupe_id = cursor.fetchone()
        if not groupe_id:
            continue
        groupe_id = groupe_id[0]
        
        # Créer tous les matchs possibles dans le groupe
        for i in range(len(equipes_ids)):
            for j in range(i+1, len(equipes_ids)):
                cursor.execute("""
                    INSERT INTO matchs (tournoi_id, equipe1_id, equipe2_id, groupe_id, date_match, phase)
                    VALUES (%s, %s, %s, %s, %s, 'Phase de groupes')
                """, (tournoi_id, equipes_ids[i], equipes_ids[j], groupe_id, date_match))
                date_match += timedelta(hours=2)  # Espacer les matchs de 2 heures
    
    conn.commit()
    conn.close()
    return True

# ----------------- Recherche intelligente -----------------
def rechercher_global(term, tournoi_id=None):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        results = {}
        
        # Recherche dans les équipes
        if tournoi_id:
            cursor.execute("SELECT id, nom, groupe FROM equipes WHERE tournoi_id=%s AND nom LIKE %s", 
                          (tournoi_id, f"%{term}%"))
        else:
            cursor.execute("SELECT id, nom, groupe FROM equipes WHERE nom LIKE %s", (f"%{term}%",))
        results['equipes'] = cursor.fetchall()
        
        # Recherche dans les joueurs
        if tournoi_id:
            cursor.execute("""
                SELECT j.id, j.nom, j.numero, e.nom 
                FROM joueurs j 
                JOIN equipes e ON j.equipe_id = e.id 
                WHERE e.tournoi_id=%s AND j.nom LIKE %s
            """, (tournoi_id, f"%{term}%"))
        else:
            cursor.execute("""
                SELECT j.id, j.nom, j.numero, e.nom 
                FROM joueurs j 
                JOIN equipes e ON j.equipe_id = e.id 
                WHERE j.nom LIKE %s
            """, (f"%{term}%",))
        results['joueurs'] = cursor.fetchall()
        
        # Recherche dans les matchs
        if tournoi_id:
            cursor.execute("""
                SELECT m.id, e1.nom, e2.nom, m.date_match 
                FROM matchs m 
                JOIN equipes e1 ON m.equipe1_id = e1.id 
                JOIN equipes e2 ON m.equipe2_id = e2.id 
                WHERE m.tournoi_id=%s AND (e1.nom LIKE %s OR e2.nom LIKE %s)
            """, (tournoi_id, f"%{term}%", f"%{term}%"))
        else:
            cursor.execute("""
                SELECT m.id, e1.nom, e2.nom, m.date_match 
                FROM matchs m 
                JOIN equipes e1 ON m.equipe1_id = e1.id 
                JOIN equipes e2 ON m.equipe2_id = e2.id 
                WHERE e1.nom LIKE %s OR e2.nom LIKE %s
            """, (f"%{term}%", f"%{term}%"))
        results['matchs'] = cursor.fetchall()
        
        conn.close()
        return results
    return {}

# ----------------- Fonctions d'administration -----------------
def show_tournament_management():
    st.title("🏆 Gestion des Tournois")
    
    tab1, tab2, tab3 = st.tabs(["Créer un tournoi", "Liste des tournois", "Configuration avancée"])
    
    with tab1:
        st.subheader("Créer un nouveau tournoi")
        with st.form("create_tournament"):
            nom = st.text_input("Nom du tournoi*")
            format_finales = st.selectbox(
                "Format des finales",
                ["Élimination directe", "Double élimination", "Round-robin"]
            )
            eq_pg = st.number_input("Équipes par groupe", min_value=2, max_value=10, value=4)
            eq_qual = st.number_input("Équipes qualifiées par groupe", min_value=1, max_value=eq_pg-1, value=2)
            
            if st.form_submit_button("Créer le tournoi"):
                if nom:
                    tid = creer_tournoi(nom, format_finales, eq_pg, eq_qual)
                    if tid:
                        st.success(f"Tournoi '{nom}' créé avec l'ID {tid}")
                    else:
                        st.error("Erreur lors de la création du tournoi")
                else:
                    st.error("Le nom du tournoi est obligatoire")
    
    with tab2:
        st.subheader("Liste des tournois")
        tournois = get_tournois()
        if tournois:
            for t in tournois:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{t[1]}** (ID: {t[0]})")
                    st.write(f"Créé le: {t[2]}")
                with col2:
                    st.write(f"Format: {t[3]}")
                    st.write(f"Équipes: {t[4]} par groupe, {t[5]} qualifiées")
                with col3:
                    if st.button("📊", key=f"stats_{t[0]}"):
                        st.session_state.current_tournoi = t[0]
                        st.rerun()
        else:
            st.info("Aucun tournoi créé pour le moment")
    
    with tab3:
        st.subheader("Configuration avancée")
        st.info("Fonctionnalités avancées de gestion des tournois")

def show_user_management():
    st.title("👥 Gestion des Utilisateurs")
    
    tab1, tab2, tab3 = st.tabs(["Créer utilisateur", "Liste des utilisateurs", "Modifier utilisateur"])
    
    with tab1:
        st.subheader("Créer un nouvel utilisateur")
        with st.form("create_user_form"):
            username = st.text_input("Nom d'utilisateur*")
            password = st.text_input("Mot de passe*", type="password")
            email = st.text_input("Email")
            full_name = st.text_input("Nom complet")
            role = st.selectbox("Rôle", ["admin", "organizer", "viewer"])
            
            # Sélection du tournoi pour les organisateurs/viewers
            tournois = get_tournois()
            tournoi_options = [("Aucun", None)] + [(t[1], t[0]) for t in tournois]
            selected_tournoi = st.selectbox(
                "Tournoi assigné (optionnel)",
                options=[opt[1] for opt in tournoi_options],
                format_func=lambda x: next((opt[0] for opt in tournoi_options if opt[1] == x), "Aucun")
            )
            
            if st.form_submit_button("Créer l'utilisateur"):
                if username and password:
                    success, message = create_user(username, password, email, full_name, role, selected_tournoi)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.error("Le nom d'utilisateur et le mot de passe sont obligatoires")
    
    with tab2:
        st.subheader("Liste des utilisateurs")
        users = get_all_users()
        if users:
            df = pd.DataFrame(users, columns=["ID", "Username", "Email", "Nom complet", "Rôle", "Actif", "Créé le"])
            st.dataframe(df)
        else:
            st.info("Aucun utilisateur enregistré")
    
    with tab3:
        st.subheader("Modifier un utilisateur")
        users = get_all_users()
        if users:
            user_options = {u[0]: f"{u[1]} ({u[3]})" for u in users}
            selected_user = st.selectbox(
                "Sélectionner un utilisateur",
                options=list(user_options.keys()),
                format_func=lambda x: user_options[x]
            )
            
            # Récupérer les détails de l'utilisateur
            user_details = next((u for u in users if u[0] == selected_user), None)
            if user_details:
                # Formulaire de modification
                with st.form("edit_user_form"):
                    username = st.text_input("Nom d'utilisateur", value=user_details[1])
                    email = st.text_input("Email", value=user_details[2])
                    full_name = st.text_input("Nom complet", value=user_details[3])
                    role = st.selectbox("Rôle", ["admin", "organizer", "viewer"], 
                                      index=["admin", "organizer", "viewer"].index(user_details[4]))
                    is_active = st.checkbox("Actif", value=bool(user_details[5]))
                    
                    # Sélection du tournoi
                    tournois = get_tournois()
                    tournoi_options = [("Aucun", None)] + [(t[1], t[0]) for t in tournois]
                    selected_tournoi = st.selectbox(
                        "Tournoi assigné",
                        options=[opt[1] for opt in tournoi_options],
                        index=next((i for i, opt in enumerate(tournoi_options) if opt[1] == user_details[6]), 0),
                        format_func=lambda x: next((opt[0] for opt in tournoi_options if opt[1] == x), "Aucun")
                    )
                    
                    if st.form_submit_button("Mettre à jour"):
                        success, message = update_user(
                            selected_user, username, email, full_name, role, is_active, selected_tournoi
                        )
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                
                # Bouton de suppression EN DEHORS du formulaire
                if st.button("Supprimer l'utilisateur", key=f"delete_{selected_user}"):
                    success, message = delete_user(selected_user)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
        else:
            st.info("Aucun utilisateur à modifier")
            
def show_global_stats():
    st.title("📊 Statistiques Globales")
    
    # Récupérer les données de tous les tournois
    tournois = get_tournois()
    
    if tournois:
        st.subheader("Aperçu des tournois")
        tournoi_data = []
        for t in tournois:
            nb_equipes = count_equipes(t[0])
            tournoi_data.append({
                "Tournoi": t[1],
                "Équipes": nb_equipes,
                "Format": t[3],
                "Créé le": t[2]
            })
        
        df_tournois = pd.DataFrame(tournoi_data)
        st.dataframe(df_tournois)
        
        # Graphique du nombre d'équipes par tournoi
        fig = px.bar(df_tournois, x='Tournoi', y='Équipes', title='Nombre d\'équipes par tournoi')
        st.plotly_chart(fig)
    else:
        st.info("Aucun tournoi disponible pour les statistiques")

def show_admin_dashboard():
    st.sidebar.title(f"👋 Bonjour {st.session_state.user_name}")
    st.sidebar.subheader(f"Rôle: {st.session_state.user_role}")
    
    menu_options = [
        "Gestion des Tournois", 
        "Gestion des Utilisateurs",
        "Statistiques Globales",
        "Déconnexion"
    ]
    
    choice = st.sidebar.selectbox("Menu", menu_options)
    
    if choice == "Gestion des Tournois":
        show_tournament_management()
    elif choice == "Gestion des Utilisateurs":
        show_user_management()
    elif choice == "Statistiques Globales":
        show_global_stats()
    elif choice == "Déconnexion":
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.user_id = None
        st.session_state.user_name = None
        st.rerun()

# ----------------- Interface Streamlit -----------------
def main():
     # Dans la fonction main(), ajoutez cette initialisation
    if 'current_equipe' not in st.session_state:
        st.session_state.current_equipe = None
    st.set_page_config(
        page_title="Système de Gestion de Tournois",
        page_icon="⚽",
        layout="wide",
        initial_sidebar_state="expanded"
       
    )

    # Initialisation de l'état de session
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.user_id = None
        st.session_state.user_name = None
        st.session_state.current_tournoi = None
        st.session_state.current_equipe = None
        st.session_state.visiteur_id = None

    # Menu principal
    if not st.session_state.logged_in:
        show_login_page()
    else:
        if st.session_state.user_role == 'admin':
            show_admin_dashboard()
        elif st.session_state.user_role in ['organizer', 'viewer']:
            show_organizer_dashboard()
        else:
            st.error("Rôle utilisateur non reconnu")

def show_login_page():
    st.title("⚽ Système de Gestion de Tournois")
    
    tab1, tab2, tab3 = st.tabs(["Connexion", "Inscription Visiteur", "Accès Public"])
    
    with tab1:
        st.header("Connexion Administrateur/Organisateur")
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        
        if st.button("Se connecter"):
            user = authenticate_user(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_id = user[0]
                st.session_state.user_role = user[2]
                st.session_state.user_name = user[3]
                st.success(f"Connecté en tant que {user[3]} ({user[2]})")
                st.rerun()
            else:
                st.error("Nom d'utilisateur ou mot de passe incorrect")
    
    with tab2:
        st.header("Inscription Visiteur")
        nom = st.text_input("Nom complet")
        email = st.text_input("Email")
        telephone = st.text_input("Téléphone")
        preferences = st.text_area("Préférences (clubs favoris, types de matchs, etc.)")
        
        if st.button("S'inscrire comme visiteur"):
            if nom:
                success, message, visiteur_id = create_visiteur(nom, email, telephone, preferences)
                if success:
                    st.session_state.visiteur_id = visiteur_id
                    st.success(message)
                else:
                    st.error(message)
            else:
                st.error("Veuillez saisir votre nom")
    
    with tab3:
        st.header("Accès Public aux Tournois")
        tournois = get_tournois_public()
        
        if tournois:
            st.subheader("Tournois en cours et à venir")
            for tournoi in tournois:
                with st.expander(f"{tournoi[1]} - {tournoi[2]} au {tournoi[3]} à {tournoi[4]}"):
                    st.write(f"Statut: {tournoi[6]}")
                    st.write(f"Description: {tournoi[5]}")
                    
                    # Afficher le classement
                    st.subheader("Classement")
                    classement = get_classement_public(tournoi[0])
                    if classement:
                        df_classement = pd.DataFrame(classement, columns=[
                            "Équipe", "Groupe", "MJ", "V", "N", "D", "BP", "BC", "Pts"
                        ])
                        st.dataframe(df_classement)
                    else:
                        st.info("Classement non disponible")
                    
                    # Afficher les prochains matchs
                    st.subheader("Prochains matchs")
                    matchs = get_prochains_matchs(tournoi[0])
                    if matchs:
                        for match in matchs:
                            st.write(f"{match[0]} vs {match[1]} - {match[2]} à {match[3]}")
                    else:
                        st.info("Aucun match programmé")
                    
                    # Bouton d'abonnement pour les visiteurs
                    if st.session_state.visiteur_id:
                        if st.button(f"S'abonner à {tournoi[1]}", key=f"sub_{tournoi[0]}"):
                            success, message = subscribe_visiteur_to_tournoi(st.session_state.visiteur_id, tournoi[0])
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
        else:
            st.info("Aucun tournoi disponible pour le moment")

def show_organizer_dashboard():
    st.sidebar.title(f"👋 Bonjour {st.session_state.user_name}")
    st.sidebar.subheader(f"Rôle: {st.session_state.user_role}")
    
    # Sélection du tournoi
    tournois = get_tournois()
    if tournois:
        tournoi_options = {t[0]: t[1] for t in tournois}
        selected_tournoi = st.sidebar.selectbox(
            "Sélectionner un tournoi",
            options=list(tournoi_options.keys()),
            format_func=lambda x: tournoi_options[x]
        )
        st.session_state.current_tournoi = selected_tournoi
        
        # Afficher l'équipe sélectionnée si elle existe
        if hasattr(st.session_state, 'current_equipe') and st.session_state.current_equipe:
            equipes = get_equipes(st.session_state.current_tournoi)
            equipe_nom = next((e[1] for e in equipes if e[0] == st.session_state.current_equipe), "Inconnue")
            st.sidebar.info(f"Équipe sélectionnée: {equipe_nom}")
    else:
        st.sidebar.info("Aucun tournoi disponible")
        st.session_state.current_tournoi = None
    
    # Le reste du menu reste inchangé...
    
    # Menu selon votre demande
    menu_options = [
        "Dashboard", 
        "Créer tournoi", 
        "Équipes", 
        "Droits Match",  
        "Joueurs",       
        "Tirage", 
        "Calendrier", 
        "Résultats",
        "Statistiques",
        "Statistiques Avancées",  
        "Phase finale",
        "Groupes & Matchs",
        "Déconnexion"
    ]
    
    choice = st.sidebar.selectbox("Menu", menu_options)
    
    if choice == "Dashboard":
        show_dashboard()
    elif choice == "Créer tournoi":
        show_creer_tournoi()
    elif choice == "Équipes":
        show_equipes()
    elif choice == "Droits Match":
        show_droits_match()
    elif choice == "Joueurs":
        show_joueurs()
    elif choice == "Tirage":
        show_tirage()
    elif choice == "Calendrier":
        show_calendrier()
    elif choice == "Résultats":
        show_resultats()
    elif choice == "Statistiques":
        show_statistiques()
    elif choice == "Statistiques Avancées":
        show_statistiques_avancees()
    elif choice == "Phase finale":
        show_phase_finale()
    elif choice == "Groupes & Matchs":
        show_groupes_matchs()
    elif choice == "Déconnexion":
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.user_id = None
        st.session_state.user_name = None
        st.rerun()

# ----------------- Nouveaux menus selon votre demande -----------------
def show_dashboard():
    if not st.session_state.current_tournoi:
        st.warning("Veuillez sélectionner un tournoi dans la sidebar")
        return
    
    tournoi_details = get_tournoi_details(st.session_state.current_tournoi)
    if not tournoi_details:
        st.error("Tournoi non trouvé")
        return
    
    st.title(f"📊 Dashboard - {tournoi_details[1]}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        nb_equipes = count_equipes(st.session_state.current_tournoi)
        st.metric("Nombre d'équipes", nb_equipes)
    
    with col2:
        groupes = get_groupes(st.session_state.current_tournoi)
        st.metric("Nombre de groupes", len(groupes))
    
    with col3:
        matchs = get_matchs(st.session_state.current_tournoi)
        st.metric("Nombre de matchs", len(matchs))
    
    with col4:
        droits = get_droits_match(st.session_state.current_tournoi)
        if droits:
            payes = sum(1 for d in droits if d[3])
            pourcentage = (payes / len(droits)) * 100
            st.metric("Droits payés", f"{pourcentage:.1f}%")
        else:
            st.metric("Droits payés", "0%")
    
    # Derniers matchs
    st.subheader("📅 Derniers matchs")
    matchs = get_matchs(st.session_state.current_tournoi)
    if matchs:
        for match in matchs[-5:]:
            score_text = f"{match[5]} - {match[6]}" if match[5] is not None and match[6] is not None else "À venir"
            st.write(f"**{match[1]}** vs **{match[2]}** ({match[3]}) - {score_text}")
    else:
        st.info("Aucun match programmé")

def show_creer_tournoi():
    st.title("🏆 Créer un nouveau tournoi")
    
    with st.form("create_tournament_form"):
        nom = st.text_input("Nom du tournoi*")
        format_finales = st.selectbox(
            "Format des finales",
            ["Élimination directe", "Double élimination", "Round-robin"]
        )
        eq_pg = st.number_input("Équipes par groupe", min_value=2, max_value=10, value=4)
        eq_qual = st.number_input("Équipes qualifiées par groupe", min_value=1, max_value=eq_pg-1, value=2)
        date_debut = st.date_input("Date de début")
        date_fin = st.date_input("Date de fin")
        lieu = st.text_input("Lieu")
        description = st.text_area("Description")
        
        if st.form_submit_button("Créer le tournoi"):
            if nom:
                tid = creer_tournoi(nom, format_finales, eq_pg, eq_qual)
                if tid:
                    st.success(f"Tournoi '{nom}' créé avec l'ID {tid}")
                else:
                    st.error("Erreur lors de la création du tournoi")
            else:
                st.error("Le nom du tournoi est obligatoire")

def show_equipes():
    if not st.session_state.current_tournoi:
        st.warning("Veuillez sélectionner un tournoi dans la sidebar")
        return
    
    st.title("👥 Gestion des Équipes")
    
    # Récupérer les équipes du tournoi
    equipes = get_equipes(st.session_state.current_tournoi)
    
    # Ajouter un sélecteur d'équipe courant
    if equipes:
        equipe_options = {e[0]: e[1] for e in equipes}
        selected_equipe = st.selectbox(
            "Sélectionner une équipe à gérer",
            options=list(equipe_options.keys()),
            format_func=lambda x: equipe_options[x],
            key="equipe_selector"
        )
        st.session_state.current_equipe = selected_equipe
    else:
        st.session_state.current_equipe = None
    
    tab1, tab2 = st.tabs(["Ajouter des équipes", "Liste des équipes"])
    
    # Le reste du code reste inchangé...
    with tab1:
        st.subheader("Ajouter des équipes")
        with st.form("add_teams_form"):
            team_names = st.text_area("Noms des équipes (un par ligne)")
            if st.form_submit_button("Ajouter les équipes"):
                if team_names:
                    teams = [name.strip() for name in team_names.split('\n') if name.strip()]
                    if ajouter_equipes(st.session_state.current_tournoi, teams):
                        st.success(f"{len(teams)} équipes ajoutées avec succès")
                        st.rerun()
                    else:
                        st.error("Erreur lors de l'ajout des équipes")
                else:
                    st.error("Veuillez saisir au moins un nom d'équipe")
    
    with tab2:
        st.subheader("Liste des équipes")
        if equipes:
            for eq in equipes:
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    st.write(f"**{eq[1]}**")
                    st.write(f"Groupe: {eq[2] or 'Non assigné'} - Numéro: {eq[3] or 'N/A'}")
                with col2:
                    joueurs = get_joueurs(eq[0])
                    st.write(f"{len(joueurs)} joueurs")
                with col3:
                    # Bouton pour définir comme équipe courante
                    if st.button("👥 Sélectionner", key=f"select_{eq[0]}"):
                        st.session_state.current_equipe = eq[0]
                        st.success(f"Équipe {eq[1]} sélectionnée")
                        st.rerun()
                with col4:
                    if st.button("📋 PDF", key=f"pdf_{eq[0]}"):
                        pdf_data = generer_fiche_equipe_pdf(eq[0])
                        if pdf_data:
                            st.download_button(
                                label="Télécharger",
                                data=pdf_data,
                                file_name=f"fiche_equipe_{eq[1]}.pdf",
                                mime="application/pdf",
                                key=f"dl_{eq[0]}"
                            )
        else:
            st.info("Aucune équipe dans ce tournoi")

def show_droits_match():
    if not st.session_state.current_tournoi:
        st.warning("Veuillez sélectionner un tournoi dans la sidebar")
        return
    
    st.title("💰 Droits de Match")
    
    tab1, tab2 = st.tabs(["Définir droits", "État des paiements"])
    
    with tab1:
        st.subheader("Définir les droits de match")
        equipes = get_equipes(st.session_state.current_tournoi)
        if equipes:
            selected_equipe = st.selectbox(
                "Sélectionner une équipe",
                options=[e[0] for e in equipes],
                format_func=lambda x: next(e[1] for e in equipes if e[0] == x)
            )
            
            montant = st.number_input("Montant (€)", min_value=0.0, value=100.0, step=10.0)
            date_limite = st.date_input("Date limite de paiement")
            
            if st.button("Définir le droit de match"):
                if set_droit_match(st.session_state.current_tournoi, selected_equipe, montant, date_limite):
                    st.success("Droit de match défini avec succès")
                else:
                    st.error("Erreur lors de la définition du droit de match")
        else:
            st.info("Aucune équipe dans ce tournoi")
    
    with tab2:
        st.subheader("État des paiements")
        droits = get_droits_match(st.session_state.current_tournoi)
        if droits:
            total = sum(d[2] for d in droits)
            paye = sum(d[2] for d in droits if d[3])
            reste = total - paye
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total à percevoir", f"{total:.2f} €")
            col2.metric("Déjà perçu", f"{paye:.2f} €")
            col3.metric("Reste à percevoir", f"{reste:.2f} €")
            
            for d in droits:
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    st.write(f"**{d[1]}**")
                with col2:
                    st.write(f"{d[2]} €")
                with col3:
                    status = "✅ Payé" if d[3] else "❌ Impayé"
                    st.write(status)
                with col4:
                    if not d[3]:
                        if st.button("💰", key=f"pay_{d[0]}"):
                            if payer_droit_match(d[0]):
                                st.success("Paiement enregistré")
                                st.rerun()
        else:
            st.info("Aucun droit de match défini")

def show_joueurs():
    if not st.session_state.current_tournoi:
        st.warning("Veuillez sélectionner un tournoi dans la sidebar")
        return
    
    if not st.session_state.current_equipe:
        st.warning("Veuillez d'abord sélectionner une équipe dans la section 'Équipes'")
        if st.button("Aller à la section Équipes"):
            st.session_state.menu_choice = "Équipes"
            st.rerun()
        return
    
    # Le reste du code de la fonction show_joueurs()...
    
    # Récupérer le nom de l'équipe
    equipes = get_equipes(st.session_state.current_tournoi)
    equipe_nom = next((e[1] for e in equipes if e[0] == st.session_state.current_equipe), "Équipe inconnue")
    
    st.title(f"👤 Gestion des Joueurs - {equipe_nom}")
    
    tab1, tab2, tab3 = st.tabs(["Ajouter un joueur", "Liste des joueurs", "Suspensions & Cartons"])
    
    with tab1:
        st.subheader("Ajouter un nouveau joueur")
        with st.form("add_player"):
            nom = st.text_input("Nom du joueur*")
            numero = st.number_input("Numéro*", min_value=1, max_value=99, step=1)
            poste = st.selectbox(
                "Poste",
                ["Gardien", "Défenseur", "Milieu", "Attaquant", "Entraîneur", "Remplaçant"]
            )
            
            if st.form_submit_button("Ajouter le joueur"):
                if nom and numero:
                    success, message = ajouter_joueur(st.session_state.current_equipe, nom, numero, poste)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.error("Le nom et le numéro sont obligatoires")
    
    with tab2:
        st.subheader("Liste des joueurs")
        joueurs = get_joueurs(st.session_state.current_equipe)
        if joueurs:
            for j in joueurs:
                col1, col2, col3, col4 = st.columns([3, 1, 2, 1])
                with col1:
                    st.write(f"**{j[1]}**")
                with col2:
                    st.write(f"#{j[2]}")
                with col3:
                    st.write(j[3])
                with col4:
                    # Formulaire de modification
                    with st.form(f"edit_form_{j[0]}"):
                        new_nom = st.text_input("Nom", value=j[1], key=f"name_{j[0]}")
                        new_numero = st.number_input("Numéro", value=j[2], key=f"num_{j[0]}")
                        new_poste = st.selectbox(
                            "Poste",
                            ["Gardien", "Défenseur", "Milieu", "Attaquant", "Entraîneur", "Remplaçant"],
                            index=["Gardien", "Défenseur", "Milieu", "Attaquant", "Entraîneur", "Remplaçant"].index(j[3]),
                            key=f"pos_{j[0]}"
                        )
                        if st.form_submit_button("Modifier"):
                            if modifier_joueur(j[0], new_nom, new_numero, new_poste):
                                st.success("Joueur modifié")
                                st.rerun()
                            else:
                                st.error("Erreur modification")
                    
                    # Bouton de suppression EN DEHORS du formulaire
                    if st.button("🗑️ Supprimer", key=f"del_{j[0]}"):
                        if supprimer_joueur(j[0]):
                            st.success("Joueur supprimé")
                            st.rerun()
                        else:
                            st.error("Erreur suppression")
        else:
            st.info("Aucun joueur dans cette équipe")
    
    with tab3:
        st.subheader("Suspensions et Cartons")
        joueurs = get_joueurs(st.session_state.current_equipe)
        if joueurs:
            selected_joueur = st.selectbox(
                "Sélectionner un joueur",
                options=[j[0] for j in joueurs],
                format_func=lambda x: next(j[1] for j in joueurs if j[0] == x)
            )
            
            # Afficher les suspensions
            st.write("### Suspensions")
            suspensions = get_suspensions_joueur(selected_joueur)
            if suspensions:
                for susp in suspensions:
                    st.warning(f"{susp[0]} match(s) suspendu(s) - Raison: {susp[1]} - Depuis: {susp[2]}")
            else:
                st.info("Aucune suspension active")
            
            # Afficher les cartons
            st.write("### Historique des cartons")
            cartons = get_cartons_joueur(selected_joueur)
            if cartons:
                for carton in cartons:
                    couleur = "🟨" if carton[0] == "jaune" else "🟥"
                    st.write(f"{couleur} {carton[0]} - Minute: {carton[1]} - Raison: {carton[2]} - Match: {carton[3]} ({carton[4]} vs {carton[5]})")
            else:
                st.info("Aucun carton pour ce joueur")
def show_tirage():
    if not st.session_state.current_tournoi:
        st.warning("Veuillez sélectionner un tournoi dans la sidebar")
        return
    
    st.title("🎲 Tirage au Sort")
    
    if st.button("🔀 Effectuer le tirage au sort"):
        groupes = tirage_groupes(st.session_state.current_tournoi)
        if groupes:
            st.success(f"Groupes créés: {', '.join(groupes)}")
    
    # Afficher les groupes existants
    groupes = get_groupes(st.session_state.current_tournoi)
    if groupes:
        st.subheader("Groupes existants")
        for groupe in groupes:
            with st.expander(f"Groupe {groupe[1]}"):
                equipes = get_equipes(st.session_state.current_tournoi)
                equipes_groupe = [e for e in equipes if e[2] == groupe[1]]
                for eq in equipes_groupe:
                    st.write(f"• {eq[1]} (Numéro: {eq[3]})")

def show_calendrier():
    if not st.session_state.current_tournoi:
        st.warning("Veuillez sélectionner un tournoi dans la sidebar")
        return
    
    st.title("📅 Calendrier des Matchs")
    
    if st.button("🔄 Générer le calendrier automatiquement"):
        if generer_matchs_groupes(st.session_state.current_tournoi):
            st.success("Calendrier généré avec succès")
        else:
            st.error("Erreur lors de la génération du calendrier")
    
    # Afficher les matchs
    matchs = get_matchs(st.session_state.current_tournoi)
    if matchs:
        for match in matchs:
            score_text = f"{match[5]} - {match[6]}" if match[5] is not None and match[6] is not None else "À venir"
            st.write(f"**{match[1]}** vs **{match[2]}** - {score_text} - {match[4]} - {match[3]}")
    else:
        st.info("Aucun match programmé")
    
    # Bouton pour exporter le calendrier en PDF
    if st.button("📥 Exporter le calendrier en PDF"):
        pdf_data = generer_calendrier_pdf(st.session_state.current_tournoi)
        if pdf_data:
            tournoi_nom = get_tournoi_details(st.session_state.current_tournoi)[1]
            st.download_button(
                label="Télécharger le calendrier",
                data=pdf_data,
                file_name=f"calendrier_{tournoi_nom}.pdf",
                mime="application/pdf"
            )

def show_resultats():
    if not st.session_state.current_tournoi:
        st.warning("Veuillez sélectionner un tournoi dans la sidebar")
        return
    
    st.title("⚽ Résultats des Matchs")
    
    matchs = get_matchs(st.session_state.current_tournoi)
    if matchs:
        matchs_non_joues = [m for m in matchs if m[5] is None]
        
        if matchs_non_joues:
            selected_match = st.selectbox(
                "Sélectionner un match à saisir",
                options=[m[0] for m in matchs_non_joues],
                format_func=lambda x: next(f"{m[1]} vs {m[2]} - {m[4]}" for m in matchs_non_joues if m[0] == x)
            )
            
            match_details = next((m for m in matchs_non_joues if m[0] == selected_match), None)
            if match_details:
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**{match_details[1]}**")
                    score1 = st.number_input("Score", min_value=0, key="score1")
                with col2:
                    st.write(f"**{match_details[2]}**")
                    score2 = st.number_input("Score", min_value=0, key="score2")
                
                if st.button("Enregistrer le score"):
                    if enregistrer_score(selected_match, score1, score2):
                        st.success("Score enregistré avec succès")
                        st.rerun()
        else:
            st.info("Tous les matchs ont été joués")
        
        # Afficher les résultats
        st.subheader("Résultats")
        matchs_joues = [m for m in matchs if m[5] is not None]
        for match in matchs_joues:
            st.write(f"**{match[1]}** {match[5]} - {match[6]} **{match[2]}** ({match[4]})")
    else:
        st.info("Aucun match programmé")

def show_statistiques():
    if not st.session_state.current_tournoi:
        st.warning("Veuillez sélectionner un tournoi dans la sidebar")
        return
    
    st.title("📊 Statistiques")
    
    tab1, tab2 = st.tabs(["Meilleurs buteurs", "Meilleurs joueurs"])
    
    with tab1:
        st.subheader("Meilleurs buteurs")
        buteurs = get_meilleurs_buteurs(st.session_state.current_tournoi, 10)
        if buteurs:
            df = pd.DataFrame(buteurs, columns=["Joueur", "Équipe", "Buts"])
            st.dataframe(df)
            fig = px.bar(df, x='Joueur', y='Buts', color='Équipe', title='Meilleurs buteurs')
            st.plotly_chart(fig)
        else:
            st.info("Aucune statistique de buts")
    
    with tab2:
        st.subheader("Meilleurs joueurs")
        joueurs = get_meilleurs_joueurs(st.session_state.current_tournoi, 10)
        if joueurs:
            df = pd.DataFrame(joueurs, columns=["Joueur", "Équipe", "Homme du match", "Points"])
            st.dataframe(df)
            fig = px.scatter(df, x='Homme du match', y='Points', title='Performance des joueurs')
            st.plotly_chart(fig)
        else:
            st.info("Aucune statistique de joueurs")

def show_statistiques_avancees():
    if not st.session_state.current_tournoi:
        st.warning("Veuillez sélectionner un tournoi dans la sidebar")
        return
    
    st.title("📈 Statistiques Avancées")
    
    st.subheader("Classement par groupe")
    groupes = get_groupes(st.session_state.current_tournoi)
    if groupes:
        for groupe in groupes:
            with st.expander(f"Classement - {groupe[1]}"):
                classement = get_classement(st.session_state.current_tournoi, groupe[0])
                if classement:
                    df = pd.DataFrame(classement, columns=[
                        "Équipe", "MJ", "V", "N", "D", "BP", "BC", "Pts"
                    ])
                    df["Diff"] = df["BP"] - df["BC"]
                    st.dataframe(df.sort_values(by=["Pts", "Diff"], ascending=[False, False]))
                else:
                    st.info("Aucun classement disponible")
    
    st.subheader("Graphiques avancés")
    # Ici vous pouvez ajouter plus de visualisations
    st.info("Fonctionnalités de statistiques avancées à implémenter")

def show_phase_finale():
    if not st.session_state.current_tournoi:
        st.warning("Veuillez sélectionner un tournoi dans la sidebar")
        return
    
    st.title("🏆 Phase Finale")
    
    if st.button("🎯 Générer les phases finales"):
        if generer_phases_finales(st.session_state.current_tournoi):
            st.success("Phases finales générées avec succès")
        else:
            st.error("Erreur lors de la génération des phases finales")
    
    phases = get_phases_finales(st.session_state.current_tournoi)
    if phases:
        for niveau in ['Huitième', 'Quart', 'Demi', 'Finale', 'Petite finale']:
            matchs_niveau = [p for p in phases if p[1] == niveau]
            if matchs_niveau:
                st.subheader(niveau)
                for match in matchs_niveau:
                    score_text = f"{match[4]} - {match[5]}" if match[4] is not None else "À venir"
                    st.write(f"**{match[2]}** vs **{match[3]}** - {score_text} - {match[6]}")
    else:
        st.info("Aucune phase finale programmée")

def show_groupes_matchs():
    if not st.session_state.current_tournoi:
        st.warning("Veuillez sélectionner un tournoi dans la sidebar")
        return
    
    st.title("📋 Groupes & Matchs")
    
    tab1, tab2 = st.tabs(["Groupes", "Matchs par groupe"])
    
    with tab1:
        st.subheader("Groupes du tournoi")
        groupes = get_groupes(st.session_state.current_tournoi)
        if groupes:
            for groupe in groupes:
                with st.expander(f"Groupe {groupe[1]}"):
                    equipes = get_equipes(st.session_state.current_tournoi)
                    equipes_groupe = [e for e in equipes if e[2] == groupe[1]]
                    for eq in equipes_groupe:
                        st.write(f"• {eq[1]} (Numéro: {eq[3]})")
        else:
            st.info("Aucun groupe créé")
    
    with tab2:
        st.subheader("Matchs par groupe")
        groupes = get_groupes(st.session_state.current_tournoi)
        if groupes:
            selected_groupe = st.selectbox(
                "Sélectionner un groupe",
                options=[g[0] for g in groupes],
                format_func=lambda x: next(g[1] for g in groupes if g[0] == x)
            )
            
            matchs_groupe = get_matchs_by_groupe(st.session_state.current_tournoi, selected_groupe)
            if matchs_groupe:
                for match in matchs_groupe:
                    score_text = f"{match[4]} - {match[5]}" if match[4] is not None else "À venir"
                    st.write(f"**{match[1]}** vs **{match[2]}** - {score_text} - {match[3]}")
            else:
                st.info("Aucun match dans ce groupe")
        else:
            st.info("Aucun groupe créé")

# ----------------- Styles CSS -----------------
def apply_custom_styles():
    st.markdown("""
        <style>
        .main {
            background-color: #f0f2f6;
        }
        .stButton>button {
            background-color: #4CAF50;
            color: white;
            border-radius: 5px;
            border: none;
            padding: 10px 24px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 4px 2px;
            cursor: pointer;
            transition-duration: 0.4s;
        }
        .stButton>button:hover {
            background-color: #45a049;
        }
        .stTextInput>div>div>input {
            border-radius: 5px;
            border: 1px solid #ccc;
            padding: 10px;
        }
        .stSelectbox>div>div>select {
            border-radius: 5px;
            border: 1px solid #ccc;
            padding: 10px;
        }
        .metric-card {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin: 10px 0;
        }
        </style>
    """, unsafe_allow_html=True)

# ----------------- Point d'entrée principal -----------------
if __name__ == "__main__":
    apply_custom_styles()
    main()