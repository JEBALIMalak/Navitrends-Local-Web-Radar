import sqlite3
import json
from datetime import datetime
import os

class ResultsDB:
    def __init__(self, db_path="results.db"):
        self.db_path = db_path
        self.init_db()

    def get_filtered_history(self, country=None, sector=None, limit=100):
        """Récupère l'historique filtré par pays et/ou secteur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
        SELECT id, url, score, country, sector, created_at
        FROM analyses
        WHERE 1=1
        '''
        params = []
        
        if country and country != "Tous":
            query += ' AND country = ?'
            params.append(country)
        
        if sector and sector != "Tous":
            query += ' AND sector = ?'
            params.append(sector)
        
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'url': row[1],
                'score': row[2],
                'country': row[3],
                'sector': row[4],
                'created_at': row[5]
            })
        
        conn.close()
        return results
    def get_history(self, limit=100):
        """Récupère l'historique des analyses (alias pour get_analyses)"""
        return self.get_analyses(limit=limit)

    def init_db(self):
        """Initialise la base de données avec les tables nécessaires"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table pour les résultats d'analyse
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            score INTEGER,
            country TEXT,
            sector TEXT,
            issues TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Table pour les statistiques
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_analyses INTEGER DEFAULT 0,
            average_score REAL DEFAULT 0,
            by_country TEXT,
            by_sector TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
    

    def save_analysis(self, analysis_data):
        """Sauvegarde une analyse dans la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO analyses (url, score, country, sector, issues, details)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            analysis_data['url'],
            analysis_data.get('score', 0),
            analysis_data.get('country', 'Unknown'),
            analysis_data.get('sector', 'Unknown'),
            json.dumps(analysis_data.get('issues', [])),
            json.dumps(analysis_data.get('details', {}))
        ))
        
        conn.commit()
        conn.close()
        return cursor.lastrowid
    def save_result(self, data):
        """Alias pour save_analysis pour la compatibilité avec le code existant"""
        return self.save_analysis(data)
    def get_analyses(self, limit=100, offset=0):
        """Récupère les analyses de la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, url, score, country, sector, issues, details, created_at
        FROM analyses
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'url': row[1],
                'score': row[2],
                'country': row[3],
                'sector': row[4],
                'issues': json.loads(row[5]) if row[5] else [],
                'details': json.loads(row[6]) if row[6] else {},
                'created_at': row[7]
            })
        
        conn.close()
        return results

    def get_analysis_by_url(self, url):
        """Récupère une analyse spécifique par URL"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, url, score, country, sector, issues, details, created_at
        FROM analyses
        WHERE url = ?
        ORDER BY created_at DESC
        LIMIT 1
        ''', (url,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'url': row[1],
                'score': row[2],
                'country': row[3],
                'sector': row[4],
                'issues': json.loads(row[5]) if row[5] else [],
                'details': json.loads(row[6]) if row[6] else {},
                'created_at': row[7]
            }
        return None

    def get_statistics(self):
        """Récupère les statistiques globales"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Nombre total d'analyses
        cursor.execute('SELECT COUNT(*) FROM analyses')
        total_analyses = cursor.fetchone()[0]
        
        # Score moyen
        cursor.execute('SELECT AVG(score) FROM analyses WHERE score > 0')
        average_score = cursor.fetchone()[0] or 0
        
        # Analyses par pays
        cursor.execute('''
        SELECT country, COUNT(*) as count, AVG(score) as avg_score
        FROM analyses
        WHERE country != 'Unknown'
        GROUP BY country
        ORDER BY count DESC
        ''')
        
        by_country = {}
        for row in cursor.fetchall():
            by_country[row[0]] = {
                'count': row[1],
                'average_score': round(row[2], 2) if row[2] else 0
            }
        
        # Analyses par secteur
        cursor.execute('''
        SELECT sector, COUNT(*) as count, AVG(score) as avg_score
        FROM analyses
        WHERE sector != 'Unknown'
        GROUP BY sector
        ORDER BY count DESC
        ''')
        
        by_sector = {}
        for row in cursor.fetchall():
            by_sector[row[0]] = {
                'count': row[1],
                'average_score': round(row[2], 2) if row[2] else 0
            }
        
        conn.close()
        
        return {
            'total_analyses': total_analyses,
            'average_score': round(average_score, 2),
            'by_country': by_country,
            'by_sector': by_sector
        }

    def export_to_json(self, filename="export_analyses.json"):
        """Exporte toutes les analyses en JSON"""
        analyses = self.get_analyses(limit=1000)
        
        export_data = {
            'export_date': datetime.now().isoformat(),
            'total_analyses': len(analyses),
            'analyses': analyses
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return filename

    def clear_database(self):
        """Vide complètement la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM analyses')
        cursor.execute('DELETE FROM statistics')
        cursor.execute('VACUUM')
        
        conn.commit()
        conn.close()

    def backup_database(self, backup_path=None):
        """Crée une sauvegarde de la base de données"""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_results_{timestamp}.db"
        
        # Copie simple du fichier de base de données
        if os.path.exists(self.db_path):
            with open(self.db_path, 'rb') as src, open(backup_path, 'wb') as dst:
                dst.write(src.read())
        
        return backup_path
    

# Test de la classe
if __name__ == "__main__":
    # Test de la base de données
    db = ResultsDB("test.db")
    
    # Exemple de données de test
    test_analysis = {
        'url': 'https://example.com',
        'score': 85,
        'country': 'France',
        'sector': 'technologie',
        'issues': ['HTTPS manquant', 'Titre trop long'],
        'details': {
            'https': False,
            'title': {'exists': True, 'length': 70, 'optimal': False}
        }
    }
    
    # Sauvegarde
    analysis_id = db.save_analysis(test_analysis)
    print(f"Analyse sauvegardée avec ID: {analysis_id}")
    
    # Récupération
    analyses = db.get_analyses()
    print(f"Analyses trouvées: {len(analyses)}")
    
    # Statistiques
    stats = db.get_statistics()
    print(f"Statistiques: {stats}")
    
    # Nettoyage
    db.clear_database()
    os.remove("test.db")