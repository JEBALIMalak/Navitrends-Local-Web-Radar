import json
import csv
from datetime import datetime
import os
from jinja2 import Template
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import base64
from io import BytesIO

class ReportGenerator:
    def __init__(self, output_dir="reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def generate_html_report_with_charts(self, analyses, stats, filename=None, open_after=False):
        """Génère un rapport HTML avec des diagrammes intégrés"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"webradar_report_with_charts_{timestamp}.html"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Générer les diagrammes en base64
        charts = self.generate_charts_base64(analyses, stats)
        
        # Template HTML avec les diagrammes
        html_template = """
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>WebRadar - Rapport Complet avec Diagrammes</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; text-align: center; }
                .section { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 25px; }
                .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
                .stat-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #667eea; }
                .stat-number { font-size: 2.5em; font-weight: bold; color: #667eea; margin: 10px 0; }
                .stat-label { color: #6c757d; font-size: 1.1em; }
                .chart-container { margin: 30px 0; text-align: center; }
                .chart { max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 8px; padding: 15px; background: white; }
                .chart-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 25px; margin: 30px 0; }
                .analysis-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; border-left: 4px solid #28a745; }
                .score { font-size: 1.5em; font-weight: bold; }
                .good { color: #28a745; }
                .medium { color: #ffc107; }
                .bad { color: #dc3545; }
                .issues-list { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 15px; }
                .issue-item { margin: 8px 0; padding: 10px; border-left: 3px solid #dc3545; background: #fff3f3; border-radius: 5px; }
                table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                th, td { padding: 15px; text-align: left; border-bottom: 2px solid #dee2e6; }
                th { background-color: #667eea; color: white; font-weight: bold; }
                tr:hover { background-color: #f8f9fa; }
                h2 { color: #495057; border-bottom: 3px solid #667eea; padding-bottom: 10px; }
                .timestamp { color: #6c757d; font-style: italic; text-align: center; margin-top: 30px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 WebRadar - Rapport Complet avec Diagrammes</h1>
                <p>Analyse complète des performances web - Généré le {{ generation_date }}</p>
            </div>

            <!-- Section Statistiques Globales -->
            <div class="section">
                <h2>📈 Statistiques Globales</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{{ stats.total_analyses }}</div>
                        <div class="stat-label">Sites Analysés</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number {{ 'good' if stats.average_score >= 80 else 'medium' if stats.average_score >= 60 else 'bad' }}">
                            {{ stats.average_score }}/100
                        </div>
                        <div class="stat-label">Score Moyen</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{{ analyses|length }}</div>
                        <div class="stat-label">Analyses Récentes</div>
                    </div>
                </div>
            </div>

            <!-- Section Diagrammes -->
            <div class="section">
                <h2>📊 Visualisations des Données</h2>
                <div class="chart-grid">
                    {% if charts.scores_distribution %}
                    <div class="chart-container">
                        <h3>Distribution des Scores</h3>
                        <img src="data:image/png;base64,{{ charts.scores_distribution }}" class="chart" alt="Distribution des Scores">
                    </div>
                    {% endif %}

                    {% if charts.score_pie %}
                    <div class="chart-container">
                        <h3>Répartition des Scores</h3>
                        <img src="data:image/png;base64,{{ charts.score_pie }}" class="chart" alt="Répartition des Scores">
                    </div>
                    {% endif %}

                    {% if charts.by_country %}
                    <div class="chart-container">
                        <h3>Analyses par Pays</h3>
                        <img src="data:image/png;base64,{{ charts.by_country }}" class="chart" alt="Analyses par Pays">
                    </div>
                    {% endif %}

                    {% if charts.by_sector %}
                    <div class="chart-container">
                        <h3>Analyses par Secteur</h3>
                        <img src="data:image/png;base64,{{ charts.by_sector }}" class="chart" alt="Analyses par Secteur">
                    </div>
                    {% endif %}

                    {% if charts.issues_chart %}
                    <div class="chart-container">
                        <h3>Problèmes les Plus Courants</h3>
                        <img src="data:image/png;base64,{{ charts.issues_chart }}" class="chart" alt="Problèmes les Plus Courants">
                    </div>
                    {% endif %}
                </div>
            </div>

            <!-- Section Analyses par Pays/Secteur -->
            {% if stats.by_country %}
            <div class="section">
                <h2>🌍 Analyses par Pays</h2>
                <table>
                    <tr>
                        <th>Pays</th>
                        <th>Nombre d'Analyses</th>
                        <th>Score Moyen</th>
                        <th>Performance</th>
                    </tr>
                    {% for country, data in stats.by_country.items() %}
                    <tr>
                        <td><strong>{{ country }}</strong></td>
                        <td>{{ data.count }}</td>
                        <td class="score {{ 'good' if data.average_score >= 80 else 'medium' if data.average_score >= 60 else 'bad' }}">
                            {{ data.average_score }}/100
                        </td>
                        <td>
                            {% if data.average_score >= 80 %} Excellente
                            {% elif data.average_score >= 60 %} Bonne
                            {% else %} À Améliorer
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            {% endif %}

            {% if stats.by_sector %}
            <div class="section">
                <h2>🏢 Analyses par Secteur</h2>
                <table>
                    <tr>
                        <th>Secteur</th>
                        <th>Nombre d'Analyses</th>
                        <th>Score Moyen</th>
                        <th>Performance</th>
                    </tr>
                    {% for sector, data in stats.by_sector.items() %}
                    <tr>
                        <td><strong>{{ sector }}</strong></td>
                        <td>{{ data.count }}</td>
                        <td class="score {{ 'good' if data.average_score >= 80 else 'medium' if data.average_score >= 60 else 'bad' }}">
                            {{ data.average_score }}/100
                        </td>
                        <td>
                            {% if data.average_score >= 80 %} Excellente
                            {% elif data.average_score >= 60 %} Bonne
                            {% else %} À Améliorer
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            {% endif %}

            <!-- Section Détail des Analyses -->
            <div class="section">
                <h2>📋 Détail des Analyses Récentes</h2>
                {% for analysis in analyses %}
                <div class="analysis-card">
                    <h3>🌐 <a href="{{ analysis.url }}" target="_blank">{{ analysis.url }}</a></h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 15px 0;">
                        <div>
                            <p><strong>Score:</strong> <span class="score {{ 'good' if analysis.score >= 80 else 'medium' if analysis.score >= 60 else 'bad' }}">{{ analysis.score }}/100</span></p>
                            <p><strong>Pays:</strong> {{ analysis.country }}</p>
                        </div>
                        <div>
                            <p><strong>Secteur:</strong> {{ analysis.sector }}</p>
                            <p><strong>Date:</strong> {{ analysis.created_at }}</p>
                        </div>
                    </div>
                    
                    {% if analysis.issues %}
                    <div class="issues-list">
                        <h4>⚠️ Problèmes Détectés ({{ analysis.issues|length }})</h4>
                        {% for issue in analysis.issues %}
                        <div class="issue-item">{{ issue }}</div>
                        {% endfor %}
                    </div>
                    {% else %}
                    <p style="color: #28a745; font-weight: bold;">✅ Aucun problème détecté - Site optimisé</p>
                    {% endif %}
                </div>
                {% endfor %}
            </div>

            <div class="timestamp">
                <p>Rapport généré automatiquement par WebRadar - {{ generation_date }}</p>
            </div>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(
            analyses=analyses,
            stats=stats,
            charts=charts,
            generation_date=datetime.now().strftime("%Y-%m-%d à %H:%M:%S")
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        if open_after:
            self.open_html_report(filepath)
        
        return filepath

    def generate_charts_base64(self, analyses, stats):
        """Génère tous les diagrammes en format base64 pour l'HTML"""
        import base64
        from io import BytesIO
        
        charts = {}
        
        # 1. Distribution des scores
        scores = [a['score'] for a in analyses if a['score'] is not None]
        if scores:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.hist(scores, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
            ax.set_xlabel('Score', fontsize=12)
            ax.set_ylabel('Nombre de sites', fontsize=12)
            ax.set_title('Distribution des Scores', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.set_axisbelow(True)
            
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            charts['scores_distribution'] = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
        
        # 2. Diagramme circulaire des scores
        excellent = len([a for a in analyses if a.get('score', 0) >= 80])
        good = len([a for a in analyses if 60 <= a.get('score', 0) < 80])
        poor = len([a for a in analyses if a.get('score', 0) < 60])
        
        if excellent + good + poor > 0:
            fig, ax = plt.subplots(figsize=(8, 8))
            labels = ['Excellent (80-100)', 'Bon (60-79)', 'Faible (<60)']
            sizes = [excellent, good, poor]
            colors = ['#28a745', '#ffc107', '#dc3545']
            explode = (0.1, 0, 0)  # highlight excellent
            
            ax.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
                shadow=True, startangle=90, textprops={'fontsize': 12})
            ax.axis('equal')
            ax.set_title('Répartition des Scores', fontsize=14, fontweight='bold')
            
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            charts['score_pie'] = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
        
        # 3. Graphique par pays
        if stats.get('by_country'):
            countries = list(stats['by_country'].keys())
            counts = [data['count'] for data in stats['by_country'].values()]
            
            fig, ax = plt.subplots(figsize=(12, 6))
            bars = ax.bar(countries, counts, alpha=0.7, color='lightgreen', edgecolor='black')
            ax.set_xlabel('Pays', fontsize=12)
            ax.set_ylabel('Nombre d\'analyses', fontsize=12)
            ax.set_title('Analyses par Pays', fontsize=14, fontweight='bold')
            plt.xticks(rotation=45, ha='right')
            
            # Ajouter les valeurs sur les barres
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{int(height)}', ha='center', va='bottom')
            
            plt.tight_layout()
            
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            charts['by_country'] = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
        
        # 4. Graphique par secteur
        if stats.get('by_sector'):
            sectors = list(stats['by_sector'].keys())
            counts = [data['count'] for data in stats['by_sector'].values()]
            
            fig, ax = plt.subplots(figsize=(12, 6))
            bars = ax.bar(sectors, counts, alpha=0.7, color='lightcoral', edgecolor='black')
            ax.set_xlabel('Secteur', fontsize=12)
            ax.set_ylabel('Nombre d\'analyses', fontsize=12)
            ax.set_title('Analyses par Secteur', fontsize=14, fontweight='bold')
            plt.xticks(rotation=45, ha='right')
            
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{int(height)}', ha='center', va='bottom')
            
            plt.tight_layout()
            
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            charts['by_sector'] = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
        
        # 5. Graphique des problèmes
        from collections import Counter
        all_issues = []
        for analysis in analyses:
            all_issues.extend(analysis.get('issues', []))
        
        if all_issues:
            issue_counts = Counter(all_issues)
            top_issues = issue_counts.most_common(8)  # Top 8 seulement
            
            if top_issues:
                issues, counts = zip(*top_issues)
                
                fig, ax = plt.subplots(figsize=(12, 8))
                y_pos = np.arange(len(issues))
                bars = ax.barh(y_pos, counts, alpha=0.7, color='orange', edgecolor='black')
                ax.set_yticks(y_pos)
                ax.set_yticklabels(issues, fontsize=11)
                ax.set_xlabel('Nombre d\'occurrences', fontsize=12)
                ax.set_title('Top 8 des Problèmes Rencontrés', fontsize=14, fontweight='bold')
                
                # Ajouter les valeurs à droite des barres
                for i, (bar, count) in enumerate(zip(bars, counts)):
                    ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2.,
                            f'{count}', ha='left', va='center', fontsize=11)
                
                plt.tight_layout()
                
                buf = BytesIO()
                plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
                buf.seek(0)
                charts['issues_chart'] = base64.b64encode(buf.read()).decode('utf-8')
                plt.close(fig)
        
        return charts
    def generate_html_report(self, analyses, stats, filename=None, open_after=False):
        """Génère un rapport HTML complet et optionnellement l'ouvre"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"webradar_report_{timestamp}.html"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Template HTML avec Jinja2
        html_template = """
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>WebRadar - Rapport d'Analyses</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }
                .stats-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
                .analysis-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 15px; }
                .score { font-size: 24px; font-weight: bold; }
                .good { color: #28a745; }
                .medium { color: #ffc107; }
                .bad { color: #dc3545; }
                .issues-list { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 10px; }
                .issue-item { margin: 5px 0; padding: 5px; border-left: 3px solid #dc3545; background: #fff3f3; }
                table { width: 100%; border-collapse: collapse; margin: 15px 0; }
                th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
                th { background-color: #667eea; color: white; }
                tr:hover { background-color: #f5f5f5; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 WebRadar - Rapport d'Analyses</h1>
                <p>Généré le {{ generation_date }}</p>
            </div>

            <div class="stats-card">
                <h2>📈 Statistiques Globales</h2>
                <p><strong>Total d'analyses:</strong> {{ stats.total_analyses }}</p>
                <p><strong>Score moyen:</strong> <span class="score {{ 'good' if stats.average_score >= 80 else 'medium' if stats.average_score >= 60 else 'bad' }}">{{ stats.average_score }}/100</span></p>
            </div>

            {% if stats.by_country %}
            <div class="stats-card">
                <h2>🌍 Analyses par Pays</h2>
                <table>
                    <tr>
                        <th>Pays</th>
                        <th>Nombre d'analyses</th>
                        <th>Score moyen</th>
                    </tr>
                    {% for country, data in stats.by_country.items() %}
                    <tr>
                        <td>{{ country }}</td>
                        <td>{{ data.count }}</td>
                        <td class="{{ 'good' if data.average_score >= 80 else 'medium' if data.average_score >= 60 else 'bad' }}">{{ data.average_score }}/100</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            {% endif %}

            {% if stats.by_sector %}
            <div class="stats-card">
                <h2>🏢 Analyses par Secteur</h2>
                <table>
                    <tr>
                        <th>Secteur</th>
                        <th>Nombre d'analyses</th>
                        <th>Score moyen</th>
                    </tr>
                    {% for sector, data in stats.by_sector.items() %}
                    <tr>
                        <td>{{ sector }}</td>
                        <td>{{ data.count }}</td>
                        <td class="{{ 'good' if data.average_score >= 80 else 'medium' if data.average_score >= 60 else 'bad' }}">{{ data.average_score }}/100</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            {% endif %}

            <h2>📋 Détail des Analyses</h2>
            {% for analysis in analyses %}
            <div class="analysis-card">
                <h3><a href="{{ analysis.url }}" target="_blank">{{ analysis.url }}</a></h3>
                <p><strong>Score:</strong> <span class="score {{ 'good' if analysis.score >= 80 else 'medium' if analysis.score >= 60 else 'bad' }}">{{ analysis.score }}/100</span></p>
                <p><strong>Pays:</strong> {{ analysis.country }}</p>
                <p><strong>Secteur:</strong> {{ analysis.sector }}</p>
                <p><strong>Date:</strong> {{ analysis.created_at }}</p>
                
                {% if analysis.issues %}
                <div class="issues-list">
                    <h4>⚠️ Problèmes détectés ({{ analysis.issues|length }})</h4>
                    {% for issue in analysis.issues %}
                    <div class="issue-item">{{ issue }}</div>
                    {% endfor %}
                </div>
                {% else %}
                <p>✅ Aucun problème détecté</p>
                {% endif %}
            </div>
            {% endfor %}
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(
            analyses=analyses,
            stats=stats,
            generation_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Ouvrir automatiquement si demandé
        if open_after:
            self.open_html_report(filepath)
        
        return filepath

    def open_html_report(self, filepath):
        """Ouvre le rapport HTML dans le navigateur par défaut"""
        try:
            import webbrowser
            # Convertir le chemin en URL file:// pour une meilleure compatibilité
            absolute_path = os.path.abspath(filepath)
            webbrowser.open(f'file:///{absolute_path}')
            return True
        except Exception as e:
            print(f"Erreur lors de l'ouverture du rapport: {e}")
            return False
    def generate_csv_report(self, analyses, filename=None):
        """Génère un rapport CSV"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"webradar_report_{timestamp}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['url', 'score', 'country', 'sector', 'issues_count', 'created_at']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for analysis in analyses:
                writer.writerow({
                    'url': analysis['url'],
                    'score': analysis['score'],
                    'country': analysis['country'],
                    'sector': analysis['sector'],
                    'issues_count': len(analysis['issues']),
                    'created_at': analysis['created_at']
                })
        
        return filepath

    def generate_json_report(self, analyses, stats, filename=None):
        """Génère un rapport JSON complet"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"webradar_report_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        report_data = {
            'generation_date': datetime.now().isoformat(),
            'statistics': stats,
            'analyses': analyses
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        return filepath

    def generate_visualizations(self, analyses, stats):
        """Génère des visualisations graphiques"""
        vis_dir = os.path.join(self.output_dir, "visualizations")
        os.makedirs(vis_dir, exist_ok=True)
        
        # Graphique des scores
        scores = [a['score'] for a in analyses if a['score'] is not None]
        if scores:
            plt.figure(figsize=(10, 6))
            plt.hist(scores, bins=20, alpha=0.7, color='skyblue')
            plt.xlabel('Score')
            plt.ylabel('Nombre de sites')
            plt.title('Distribution des Scores')
            plt.grid(True, alpha=0.3)
            plt.savefig(os.path.join(vis_dir, 'scores_distribution.png'))
            plt.close()
        
        # Graphique par pays (si disponible)
        if stats['by_country']:
            countries = list(stats['by_country'].keys())
            counts = [data['count'] for data in stats['by_country'].values()]
            
            plt.figure(figsize=(12, 6))
            plt.bar(countries, counts, alpha=0.7, color='lightgreen')
            plt.xlabel('Pays')
            plt.ylabel('Nombre d\'analyses')
            plt.title('Analyses par Pays')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(os.path.join(vis_dir, 'by_country.png'))
            plt.close()
        
        # Graphique par secteur (si disponible)
        if stats['by_sector']:
            sectors = list(stats['by_sector'].keys())
            counts = [data['count'] for data in stats['by_sector'].values()]
            
            plt.figure(figsize=(12, 6))
            plt.bar(sectors, counts, alpha=0.7, color='lightcoral')
            plt.xlabel('Secteur')
            plt.ylabel('Nombre d\'analyses')
            plt.title('Analyses par Secteur')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(os.path.join(vis_dir, 'by_sector.png'))
            plt.close()
        
        return vis_dir

    def generate_comprehensive_report(self, analyses, stats):
        """Génère un rapport complet avec tous les formats"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"webradar_comprehensive_{timestamp}"
        
        # Générer tous les formats
        html_file = self.generate_html_report(analyses, stats, f"{base_filename}.html")
        csv_file = self.generate_csv_report(analyses, f"{base_filename}.csv")
        json_file = self.generate_json_report(analyses, stats, f"{base_filename}.json")
        vis_dir = self.generate_visualizations(analyses, stats)
        
        return {
            'html': html_file,
            'csv': csv_file,
            'json': json_file,
            'visualizations': vis_dir
        }

# Test de la classe
if __name__ == "__main__":
    # Données de test
    test_analyses = [
        {
            'url': 'https://example.com',
            'score': 85,
            'country': 'France',
            'sector': 'technologie',
            'issues': ['HTTPS manquant', 'Titre trop long'],
            'created_at': '2024-01-15 10:30:00'
        },
        {
            'url': 'https://test.org',
            'score': 92,
            'country': 'International',
            'sector': 'education',
            'issues': [],
            'created_at': '2024-01-15 11:45:00'
        }
    ]
    
    test_stats = {
        'total_analyses': 2,
        'average_score': 88.5,
        'by_country': {
            'France': {'count': 1, 'average_score': 85},
            'International': {'count': 1, 'average_score': 92}
        },
        'by_sector': {
            'technologie': {'count': 1, 'average_score': 85},
            'education': {'count': 1, 'average_score': 92}
        }
    }
    
    # Test du générateur de rapports
    reporter = ReportGenerator("test_reports")
    
    html_report = reporter.generate_html_report(test_analyses, test_stats)
    csv_report = reporter.generate_csv_report(test_analyses)
    json_report = reporter.generate_json_report(test_analyses, test_stats)
    vis_dir = reporter.generate_visualizations(test_analyses, test_stats)
    
    print(f"Rapport HTML généré: {html_report}")
    print(f"Rapport CSV généré: {csv_report}")
    print(f"Rapport JSON généré: {json_report}")
    print(f"Visualisations générées dans: {vis_dir}")