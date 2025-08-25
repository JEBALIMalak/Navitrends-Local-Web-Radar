import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import json
from threading import Thread, Lock, Event
import os
import time
from datetime import datetime
import logging
import webbrowser
import tempfile
import shutil
from core import WebRadarETL
from core.database import ResultsDB
from utils.report_generator import ReportGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModernRadarApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Navitrends Local Web Radar Pro")
        self.root.geometry("1200x800")
        
        # Initialisation des composants
        self.etl = WebRadarETL()
        self.db = ResultsDB()
        self.report_generator = ReportGenerator()
        
        self.last_results = []
        self.lock = Lock()
        self.stop_event = Event()
        self.is_analyzing = False
        
        self._setup_ui()
        self._show_history()

    def _setup_ui(self):
        # Notebook pour les onglets
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Onglet Analyse
        self.analysis_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.analysis_frame, text="Analyse de Sites")
        
        # Onglet Historique
        self.history_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.history_frame, text="Historique des Analyses")
        
        # Onglet Rapports
        self.reports_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.reports_frame, text="Rapports Commerciaux")
        
        # Configuration de l'onglet Analyse
        self._setup_analysis_tab()
        self._setup_history_tab()
        self._setup_reports_tab()
        
        # Barre de statut
        self.status_var = tk.StringVar()
        self.status_var.set("Prêt")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _setup_analysis_tab(self):
        # Frame pour l'import
        import_frame = ttk.Frame(self.analysis_frame)
        import_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(import_frame, text="Importer URLs", command=self._import_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(import_frame, text="Importer depuis CSV", command=self._import_csv).pack(side=tk.LEFT, padx=5)
        
        # Filtres
        filter_frame = ttk.LabelFrame(self.analysis_frame, text="Filtres de Ciblage", padding=5)
        filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(filter_frame, text="Pays:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.country_var = tk.StringVar()
        country_combo = ttk.Combobox(filter_frame, textvariable=self.country_var, 
                                    values=["France", "UK", "Tunisia", "Saudi Arabia", "Tous"])
        country_combo.set("Tous")
        country_combo.grid(row=0, column=1, padx=5)
        
        ttk.Label(filter_frame, text="Secteur:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.sector_var = tk.StringVar()
        sector_combo = ttk.Combobox(filter_frame, textvariable=self.sector_var, 
                                   values=["Immobilier", "Juridique", "Médical", "Restauration", "Hôtellerie", "Tous"])
        sector_combo.set("Tous")
        sector_combo.grid(row=0, column=3, padx=5)
        
        # Zone de saisie URLs
        ttk.Label(self.analysis_frame, text="URLs à analyser (1 par ligne)", font=('Arial', 12)).pack(anchor=tk.W, pady=(10, 5))
        self.url_input = scrolledtext.ScrolledText(self.analysis_frame, height=8)
        self.url_input.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Boutons d'action
        btn_frame = ttk.Frame(self.analysis_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.analyze_btn = ttk.Button(btn_frame, text="Démarrer l'Analyse", command=self._start_analysis)
        self.analyze_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="Arrêter", command=self._stop_analysis, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.export_btn = ttk.Button(btn_frame, text="Exporter Résultats", command=self._export_results)
        self.export_btn.pack(side=tk.LEFT, padx=5)
        self.export_btn.config(state=tk.DISABLED)
        
        # Barre de progression
        self.progress = ttk.Progressbar(self.analysis_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=5)
        
        # Tableau des résultats
        results_frame = ttk.Frame(self.analysis_frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.tree = ttk.Treeview(results_frame, columns=("url", "score", "pays", "secteur", "issues"), show='headings', height=12)
        self.tree.heading("url", text="URL")
        self.tree.heading("score", text="Score")
        self.tree.heading("pays", text="Pays")
        self.tree.heading("secteur", text="Secteur")
        self.tree.heading("issues", text="Problèmes")
        
        self.tree.column("url", width=300)
        self.tree.column("score", width=80)
        self.tree.column("pays", width=100)
        self.tree.column("secteur", width=120)
        self.tree.column("issues", width=200)
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<Double-1>", self._show_details)

    def _setup_history_tab(self):
        # Filtres historiques
        hist_filter_frame = ttk.Frame(self.history_frame)
        hist_filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(hist_filter_frame, text="Pays:").pack(side=tk.LEFT, padx=5)
        self.hist_country_var = tk.StringVar()
        hist_country_combo = ttk.Combobox(hist_filter_frame, textvariable=self.hist_country_var, 
                                         values=["France", "UK", "Tunisia", "Saudi Arabia", "Tous"])
        hist_country_combo.set("Tous")
        hist_country_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(hist_filter_frame, text="Secteur:").pack(side=tk.LEFT, padx=5)
        self.hist_sector_var = tk.StringVar()
        hist_sector_combo = ttk.Combobox(hist_filter_frame, textvariable=self.hist_sector_var, 
                                        values=["Immobilier", "Juridique", "Médical", "Restauration", "Hôtellerie", "Tous"])
        hist_sector_combo.set("Tous")
        hist_sector_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(hist_filter_frame, text="Filtrer", command=self._filter_history).pack(side=tk.LEFT, padx=5)
        
        # Tableau historique
        hist_tree_frame = ttk.Frame(self.history_frame)
        hist_tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.hist_tree = ttk.Treeview(hist_tree_frame, columns=("url", "score", "pays", "secteur", "date"), show='headings', height=15)
        self.hist_tree.heading("url", text="URL")
        self.hist_tree.heading("score", text="Score")
        self.hist_tree.heading("pays", text="Pays")
        self.hist_tree.heading("secteur", text="Secteur")
        self.hist_tree.heading("date", text="Date Analyse")
        
        self.hist_tree.column("url", width=300)
        self.hist_tree.column("score", width=80)
        self.hist_tree.column("pays", width=100)
        self.hist_tree.column("secteur", width=120)
        self.hist_tree.column("date", width=120)
        
        hist_scrollbar = ttk.Scrollbar(hist_tree_frame, orient=tk.VERTICAL, command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=hist_scrollbar.set)
        
        self.hist_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hist_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.hist_tree.bind("<Double-1>", self._show_hist_details)
    """"
    def _setup_reports_tab(self):
        # Options de rapport
        report_options = ttk.LabelFrame(self.reports_frame, text="Options de Rapport", padding=10)
        report_options.pack(fill=tk.X, pady=5)
        
        ttk.Label(report_options, text="Type de rapport:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.report_type_var = tk.StringVar()
        report_type_combo = ttk.Combobox(report_options, textvariable=self.report_type_var, 
                                        values=["Rapport Complet", "Sites Prioritaires", "Par Secteur", "Par Pays"])
        report_type_combo.set("Rapport Complet")
        report_type_combo.grid(row=0, column=1, padx=5)
        
        ttk.Label(report_options, text="Format:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.report_format_var = tk.StringVar()
        report_format_combo = ttk.Combobox(report_options, textvariable=self.report_format_var, 
                                          values=["CSV", "JSON", "PDF"])
        report_format_combo.set("CSV")
        report_format_combo.grid(row=0, column=3, padx=5)
        
        ttk.Button(report_options, text="Générer Rapport", command=self._generate_report).grid(row=0, column=4, padx=5)
        
        # Zone d'aperçu du rapport
        ttk.Label(self.reports_frame, text="Aperçu du Rapport", font=('Arial', 12)).pack(anchor=tk.W, pady=(10, 5))
        self.report_preview = scrolledtext.ScrolledText(self.reports_frame, height=15)
        self.report_preview.pack(fill=tk.BOTH, expand=True, pady=5)
        self.report_preview.config(state=tk.DISABLED)
        """
    def _setup_reports_tab(self):
        # Options de rapport
        report_options = ttk.LabelFrame(self.reports_frame, text="Options de Rapport", padding=10)
        report_options.pack(fill=tk.X, pady=5)
        
        ttk.Label(report_options, text="Type de rapport:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.report_type_var = tk.StringVar()
        report_type_combo = ttk.Combobox(report_options, textvariable=self.report_type_var, 
                                        values=["Rapport Complet", "Sites Prioritaires", "Par Secteur", "Par Pays"])
        report_type_combo.set("Rapport Complet")
        report_type_combo.grid(row=0, column=1, padx=5)
        
        ttk.Label(report_options, text="Format:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.report_format_var = tk.StringVar()
        report_format_combo = ttk.Combobox(report_options, textvariable=self.report_format_var, 
                                        values=["CSV", "JSON", "PDF", "HTML"])  # AJOUT DE HTML
        report_format_combo.set("CSV")
        report_format_combo.grid(row=0, column=3, padx=5)
        
        ttk.Button(report_options, text="Générer Rapport", command=self._generate_report).grid(row=0, column=4, padx=5)
        
        # Ajouter un bouton pour ouvrir le dossier des rapports
        ttk.Button(report_options, text="Ouvrir Dossier Rapports", 
                command=self._open_reports_folder).grid(row=0, column=5, padx=5)
        
        # Zone d'aperçu du rapport
        ttk.Label(self.reports_frame, text="Aperçu du Rapport", font=('Arial', 12)).pack(anchor=tk.W, pady=(10, 5))
        self.report_preview = scrolledtext.ScrolledText(self.reports_frame, height=15)
        self.report_preview.pack(fill=tk.BOTH, expand=True, pady=5)
        self.report_preview.config(state=tk.DISABLED)

    def _import_file(self):
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier d'URLs",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not file_path:
            return

        urls = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and self.etl.is_valid_url(line):
                        urls.append(line)
        except Exception as e:
            messagebox.showerror("Erreur Fichier", f"Impossible de lire le fichier: {e}")
            return

        if urls:
            self.url_input.delete("1.0", tk.END)
            self.url_input.insert(tk.END, "\n".join(urls))
            messagebox.showinfo("Import Réussi", f"{len(urls)} URLs importées avec succès!")

    def _import_csv(self):
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            import csv
            urls = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and self.etl.is_valid_url(row[0]):
                        urls.append(row[0])
            
            if urls:
                self.url_input.delete("1.0", tk.END)
                self.url_input.insert(tk.END, "\n".join(urls))
                messagebox.showinfo("Import Réussi", f"{len(urls)} URLs importées depuis CSV!")
        except Exception as e:
            messagebox.showerror("Erreur CSV", f"Impossible de lire le fichier CSV: {e}")

    def _start_analysis(self):
        urls = [u.strip() for u in self.url_input.get("1.0", tk.END).split("\n") if u.strip() and self.etl.is_valid_url(u.strip())]
        if not urls:
            messagebox.showwarning("Erreur Saisie", "Veuillez entrer au moins une URL valide")
            return

        # Appliquer les filtres
        country = self.country_var.get() if self.country_var.get() != "Tous" else None
        sector = self.sector_var.get() if self.sector_var.get() != "Tous" else None
        
        self.is_analyzing = True
        self.analyze_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.export_btn.config(state=tk.DISABLED)
        self.progress.start()
        self.status_var.set("Analyse en cours...")
        self.last_results = []
        self.stop_event.clear()

        # Thread pour l'analyse
        Thread(target=self._run_analysis_threads, args=(urls, country, sector), daemon=True).start()

    def _stop_analysis(self):
        self.stop_event.set()
        self.status_var.set("Arrêt demandé...")

    def _run_analysis_threads(self, urls, country_filter, sector_filter):
        threads = []
        results = []

        def analyze(url):
            if self.stop_event.is_set():
                return
                
            try:
                result = self.etl.process_site(url, country_filter, sector_filter)
                with self.lock:
                    results.append(result)
                    self.db.save_result(result)
            except Exception as e:
                logger.error(f"Erreur lors de l'analyse de {url}: {e}")

        # Limiter le nombre de threads simultanés
        max_threads = 5
        for i in range(0, len(urls), max_threads):
            if self.stop_event.is_set():
                break
                
            batch = urls[i:i+max_threads]
            batch_threads = []
            
            for url in batch:
                if self.stop_event.is_set():
                    break
                    
                t = Thread(target=analyze, args=(url,))
                t.start()
                batch_threads.append(t)
            
            for t in batch_threads:
                t.join()
            
            # Mettre à jour l'interface après chaque batch
            self.root.after(0, self._update_results, results.copy())
            results.clear()

        self.root.after(0, self._analysis_complete)

    def _update_results(self, batch_results):
        for result in batch_results:
            issues_text = f"{len(result['issues'])} problèmes" if result['issues'] else "Aucun problème"
            score = result['score']
            tag = "good" if score >= 80 else "average" if score >= 60 else "poor"
            
            self.tree.insert("", tk.END, values=(
                result['url'], 
                f"{score}/100",
                result.get('country', 'N/A'),
                result.get('sector', 'N/A'),
                issues_text
            ), tags=(tag,))
            
            self.last_results.append(result)

        self.tree.tag_configure("good", background="#e6ffe6")
        self.tree.tag_configure("average", background="#fff9e6")
        self.tree.tag_configure("poor", background="#ffe6e6")

    def _analysis_complete(self):
        self.is_analyzing = False
        self.analyze_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.export_btn.config(state=tk.NORMAL)
        self.progress.stop()
        
        if self.stop_event.is_set():
            self.status_var.set("Analyse interrompue")
            messagebox.showinfo("Analyse", "Analyse interrompue par l'utilisateur")
        else:
            self.status_var.set(f"Analyse terminée - {len(self.last_results)} sites analysés")
            messagebox.showinfo("Analyse", f"Analyse terminée! {len(self.last_results)} sites analysés.")
        
        # Rafraîchir l'historique
        self._show_history()

    def _export_results(self):
        if not self.last_results:
            messagebox.showwarning("Export", "Aucun résultat à exporter")
            return
            
        filename = filedialog.asksaveasfilename(
            title="Exporter les résultats",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                if filename.endswith('.csv'):
                    self.report_generator.export_to_csv(self.last_results, filename)
                else:
                    self.report_generator.export_to_json(self.last_results, filename)
                
                messagebox.showinfo("Export Réussi", f"Résultats exportés vers {filename}")
            except Exception as e:
                messagebox.showerror("Erreur Export", f"Erreur lors de l'export: {e}")

    def _show_details(self, event):
        sel = self.tree.selection()
        if not sel:
            return
            
        item = self.tree.item(sel[0])
        url = item['values'][0]
        res = next((r for r in self.last_results if r['url'] == url), None)
        
        if res:
            self._show_result_details(res, "Détails de l'analyse")

    def _show_hist_details(self, event):
        sel = self.hist_tree.selection()
        if not sel:
            return
            
        item = self.hist_tree.item(sel[0])
        url = item['values'][0]
        res = self.db.get_result(url)
        
        if res:
            self._show_result_details(res, "Détails de l'analyse historique")

    def _show_result_details(self, result, title):
        detail_win = tk.Toplevel(self.root)
        detail_win.title(title)
        detail_win.geometry("800x600")
        
        notebook = ttk.Notebook(detail_win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Onglet Résumé
        summary_frame = ttk.Frame(notebook, padding=10)
        notebook.add(summary_frame, text="Résumé")
        
        ttk.Label(summary_frame, text=f"URL: {result['url']}", font=('Arial', 12, 'bold')).pack(anchor=tk.W)
        ttk.Label(summary_frame, text=f"Score: {result['score']}/100", font=('Arial', 12)).pack(anchor=tk.W, pady=5)
        ttk.Label(summary_frame, text=f"Pays: {result.get('country', 'N/A')}").pack(anchor=tk.W)
        ttk.Label(summary_frame, text=f"Secteur: {result.get('sector', 'N/A')}").pack(anchor=tk.W)
        
        # Problèmes détectés
        ttk.Label(summary_frame, text="Problèmes détectés:", font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(10, 5))
        issues_frame = ttk.Frame(summary_frame)
        issues_frame.pack(fill=tk.X, pady=5)
        
        if result['issues']:
            for issue in result['issues']:
                ttk.Label(issues_frame, text=f"• {issue}", foreground="red").pack(anchor=tk.W)
        else:
            ttk.Label(issues_frame, text="Aucun problème détecté", foreground="green").pack(anchor=tk.W)
        
        # Onglet Détails Techniques
        tech_frame = ttk.Frame(notebook, padding=10)
        notebook.add(tech_frame, text="Détails Techniques")
        
        tech_text = scrolledtext.ScrolledText(tech_frame, wrap=tk.WORD)
        tech_text.pack(fill=tk.BOTH, expand=True)
        
        details = result.get('details', {})
        tech_info = f"""
DÉTAILS TECHNIQUES:

HTTPS: {'Oui' if details.get('https') else 'Non'}
Mobile-Friendly: {'Oui' if details.get('mobile', {}).get('mobileFriendly') else 'Non'}

TITRE:
  Existe: {'Oui' if details.get('title', {}).get('exists') else 'Non'}
  Contenu: {details.get('title', {}).get('content', 'N/A')}
  Longueur: {details.get('title', {}).get('length', 0)} caractères
  Optimal: {'Oui' if details.get('title', {}).get('optimal') else 'Non'}

META DESCRIPTION:
  Existe: {'Oui' if details.get('meta_description', {}).get('exists') else 'Non'}
  Contenu: {details.get('meta_description', {}).get('content', 'N/A')}
  Longueur: {details.get('meta_description', {}).get('length', 0)} caractères
  Optimal: {'Oui' if details.get('meta_description', {}).get('optimal') else 'Non'}

BALISES H1:
  Nombre: {details.get('h1', {}).get('count', 0)}
  Optimal: {'Oui' if details.get('h1', {}).get('optimal') else 'Non'}

CMS:
  Nom: {details.get('cms', {}).get('name', 'Inconnu')}
  Version: {details.get('cms', {}).get('version', 'N/A')}
  Obsolète: {'Oui' if details.get('cms', {}).get('outdated') else 'Non'}

PERFORMANCE:
  Temps de chargement: {details.get('performance', {}).get('load_time', 'N/A')} secondes
  Lent: {'Oui' if details.get('performance', {}).get('slow') else 'Non'}

COPYRIGHT:
  Année: {details.get('copyright', {}).get('year', 'N/A')}
  Obsolète: {'Oui' if details.get('copyright', {}).get('outdated') else 'Non'}

IMAGES:
  Total: {details.get('images', {}).get('total', 0)}
  Sans alt: {details.get('images', {}).get('without_alt', 0)}
  Optimal: {'Oui' if details.get('images', {}).get('optimal') else 'Non'}

LIENS:
  Total: {details.get('links', {}).get('total', 0)}
  Internes: {details.get('links', {}).get('internal', 0)}
  Externes: {details.get('links', {}).get('external', 0)}
"""
        tech_text.insert(tk.END, tech_info)
        tech_text.config(state=tk.DISABLED)
        
        # Onglet Données Brutes
        raw_frame = ttk.Frame(notebook, padding=10)
        notebook.add(raw_frame, text="Données Brutes")
        
        raw_text = scrolledtext.ScrolledText(raw_frame, wrap=tk.WORD)
        raw_text.pack(fill=tk.BOTH, expand=True)
        raw_text.insert(tk.END, json.dumps(result, indent=2, ensure_ascii=False))
        raw_text.config(state=tk.DISABLED)

    def _show_history(self):
        # Vider l'arbre
        for item in self.hist_tree.get_children():
            self.hist_tree.delete(item)
        
        # Utiliser get_analyses() au lieu de get_history() pour avoir tous les champs
        analyses = self.db.get_analyses(100)
        
        for analysis in analyses:
            # Formater les valeurs
            url = analysis.get('url', 'N/A')
            score = analysis.get('score', 0)
            country = analysis.get('country', 'N/A')
            sector = analysis.get('sector', 'N/A')
            created_at = analysis.get('created_at', 'N/A')
            
            # Formater la date si c'est un objet datetime
            if hasattr(created_at, 'strftime'):
                created_at = created_at.strftime("%Y-%m-%d %H:%M")
            elif isinstance(created_at, str) and len(created_at) > 16:
                created_at = created_at[:16]  # Tronquer si trop long
            
            # Formater le score
            score_text = f"{score}/100" if score is not None else "N/A"
            
            # Insérer dans le treeview
            self.hist_tree.insert("", tk.END, values=(
                url, 
                score_text,
                country if country and country != "Unknown" else "N/A",
                sector if sector and sector != "Unknown" else "N/A",
                created_at
            ))
    def _filter_history(self):
        country = self.hist_country_var.get() if self.hist_country_var.get() != "Tous" else None
        sector = self.hist_sector_var.get() if self.hist_sector_var.get() != "Tous" else None
        
        # Vider l'arbre
        for item in self.hist_tree.get_children():
            self.hist_tree.delete(item)
        
        # Récupérer et filtrer l'historique
        history = self.db.get_filtered_history(country, sector, 100)
        
        for item in history:
            url, score, analysis_date = item
            result = self.db.get_result(url)
            
            if result:
                self.hist_tree.insert("", tk.END, values=(
                    url, 
                    f"{score}/100",
                    result.get('country', 'N/A'),
                    result.get('sector', 'N/A'),
                    analysis_date
                ))
    def _compute_stats(self, analyses):
        # Analyses: list[dict] avec au moins url, score, country, sector, issues, created_at
        total = len(analyses)
        avg = round(sum(a.get('score', 0) or 0 for a in analyses) / total, 2) if total else 0.0

        by_country = {}
        by_sector = {}

        for a in analyses:
            c = a.get('country') or 'Inconnu'
            s = a.get('sector') or 'Inconnu'
            by_country.setdefault(c, {'count': 0, 'sum': 0})
            by_sector.setdefault(s, {'count': 0, 'sum': 0})
            score_val = a.get('score', 0) or 0
            by_country[c]['count'] += 1
            by_country[c]['sum'] += score_val
            by_sector[s]['count'] += 1
            by_sector[s]['sum'] += score_val

        # convertir en {key: {count, average_score}}
        by_country = {
            k: {'count': v['count'], 'average_score': round(v['sum']/v['count'], 2) if v['count'] else 0}
            for k, v in by_country.items()
        }
        by_sector = {
            k: {'count': v['count'], 'average_score': round(v['sum']/v['count'], 2) if v['count'] else 0}
            for k, v in by_sector.items()
        }

        return {
            'total_analyses': total,
            'average_score': avg,
            'by_country': by_country,
            'by_sector': by_sector,
        }
    """
    def _generate_report(self):
        report_type = self.report_type_var.get()
        report_format = self.report_format_var.get()
        
        # Récupérer les données selon le type de rapport
        if report_type == "Rapport Complet":
            data = self.db.get_all_results()
        elif report_type == "Sites Prioritaires":
            data = self.db.get_priority_results()
        elif report_type == "Par Secteur":
            sector = self.hist_sector_var.get() if self.hist_sector_var.get() != "Tous" else None
            data = self.db.get_results_by_sector(sector)
        elif report_type == "Par Pays":
            country = self.hist_country_var.get() if self.hist_country_var.get() != "Tous" else None
            data = self.db.get_results_by_country(country)
        else:
            data = []
        
        if not data:
            messagebox.showwarning("Rapport", "Aucune donnée à reporter")
            return
        
        # Générer le rapport
        
        try:
            if report_format == "CSV":
                report_content = self.report_generator.generate_csv_report(data, report_type)
            elif report_format == "JSON":
                report_content = self.report_generator.generate_json_report(data, report_type)
            else:  # PDF
                filename = filedialog.asksaveasfilename(
                    title="Enregistrer le rapport PDF",
                    defaultextension=".pdf",
                    filetypes=[("PDF files", "*.pdf")]
                )
                if filename:
                    self.report_generator.generate_pdf_report(data, report_type, filename)
                    messagebox.showinfo("Rapport", f"Rapport PDF généré: {filename}")
                return
            
            # Afficher l'aperçu
            self.report_preview.config(state=tk.NORMAL)
            self.report_preview.delete("1.0", tk.END)
            self.report_preview.insert(tk.END, report_content)
            self.report_preview.config(state=tk.DISABLED)
            
            # Proposer de sauvegarder
            if messagebox.askyesno("Rapport", "Voulez-vous enregistrer ce rapport?"):
                filename = filedialog.asksaveasfilename(
                    title="Enregistrer le rapport",
                    defaultextension=f".{report_format.lower()}",
                    filetypes=[(f"{report_format} files", f"*.{report_format.lower()}")]
                )
                if filename:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(report_content)
                    messagebox.showinfo("Rapport", f"Rapport enregistré: {filename}")
                    
        except Exception as e:
            messagebox.showerror("Erreur Rapport", f"Erreur lors de la génération du rapport: {e}")
        """
    """
    def _generate_report(self):
        try:
            # Récupérer données depuis la DB
            analyses = self.db.get_analyses(100)  
            stats = self.db.get_statistics()

            # Vérifier qu'on a bien des données
            if not analyses:
                messagebox.showwarning("Rapport", "Aucune donnée trouvée pour générer le rapport.")
                return
            
            # Générateur de rapport
            reporter = ReportGenerator()

            # CORRECTION: Utiliser report_format_var au lieu de report_format
            if self.report_format_var.get() == "HTML":
                report_path = reporter.generate_html_report(analyses, stats)
                if report_path:
                    import webbrowser
                    webbrowser.open(report_path)
            elif self.report_format_var.get() == "CSV":
                report_path = reporter.generate_csv_report(analyses)
            elif self.report_format_var.get() == "JSON":
                report_path = reporter.generate_json_report(analyses)
            elif self.report_format_var.get() == "PDF":
                report_path = reporter.generate_pdf_report(analyses, stats)
            else:
                messagebox.showerror("Rapport", "Format non supporté")
                return

            if report_path:
                messagebox.showinfo("Rapport", f"Rapport généré: {report_path}")
            else:
                messagebox.showerror("Rapport", "Impossible de générer le rapport")

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erreur", f"Erreur lors de la génération du rapport: {e}")
    """
    def _generate_report(self):
        try:
            # Récupérer données depuis la DB
            analyses = self.db.get_analyses(100)  
            stats = self.db.get_statistics()

            # Vérifier qu'on a bien des données
            if not analyses:
                messagebox.showwarning("Rapport", "Aucune donnée trouvée pour générer le rapport.")
                return
            
            # Générateur de rapport
            reporter = ReportGenerator()

            report_format = self.report_format_var.get()
            """
            if report_format == "HTML":
                # Générer le rapport HTML et l'ouvrir automatiquement
                report_path = reporter.generate_html_report(analyses, stats, open_after=True)
                
                # Afficher un message de confirmation dans l'aperçu
                self.report_preview.config(state=tk.NORMAL)
                self.report_preview.delete("1.0", tk.END)
                self.report_preview.insert(tk.END, f"✅ Rapport HTML généré avec succès!\n\n")
                self.report_preview.insert(tk.END, f"📁 Fichier: {report_path}\n")
                self.report_preview.insert(tk.END, f"📊 Analyses: {len(analyses)} sites\n")
                self.report_preview.insert(tk.END, f"⭐ Score moyen: {stats.get('average_score', 0)}/100\n\n")
                self.report_preview.insert(tk.END, "Le rapport a été ouvert dans votre navigateur par défaut.")
                self.report_preview.config(state=tk.DISABLED)
                
                messagebox.showinfo("Rapport HTML", f"Rapport HTML généré et ouvert!\n{report_path}")
            """
            if report_format == "HTML":
                # Utiliser la nouvelle méthode avec diagrammes
                report_path = reporter.generate_html_report_with_charts(analyses, stats, open_after=True)
                
                self.report_preview.config(state=tk.NORMAL)
                self.report_preview.delete("1.0", tk.END)
                self.report_preview.insert(tk.END, f"✅ Rapport HTML avec diagrammes généré avec succès!\n\n")
                self.report_preview.insert(tk.END, f"📁 Fichier: {report_path}\n")
                self.report_preview.insert(tk.END, f"📊 Analyses: {len(analyses)} sites\n")
                self.report_preview.insert(tk.END, f"⭐ Score moyen: {stats.get('average_score', 0)}/100\n")
                self.report_preview.insert(tk.END, f"📈 Diagrammes: {sum(1 for a in analyses if a.get('score'))} scores analysés\n\n")
                self.report_preview.insert(tk.END, "Le rapport a été ouvert dans votre navigateur avec des diagrammes intégrés.")
                self.report_preview.config(state=tk.DISABLED)    
                
            elif report_format == "CSV":
                filename = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv")]
                )
                if filename:
                    report_path = reporter.generate_csv_report(analyses, filename)
                    # Afficher l'aperçu
                    with open(report_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self._update_report_preview(content, report_path, "CSV")
                    
            elif report_format == "JSON":
                filename = filedialog.asksaveasfilename(
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json")]
                )
                if filename:
                    report_path = reporter.generate_json_report(analyses, stats, filename)
                    # Afficher l'aperçu
                    with open(report_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self._update_report_preview(content, report_path, "JSON")
                    
            elif report_format == "PDF":
                filename = filedialog.asksaveasfilename(
                    defaultextension=".pdf",
                    filetypes=[("PDF files", "*.pdf")]
                )
                if filename:
                    report_path = reporter.generate_pdf_report(analyses, stats, filename)
                    # Pour PDF, on ne peut pas afficher le contenu, donc on montre un message
                    self.report_preview.config(state=tk.NORMAL)
                    self.report_preview.delete("1.0", tk.END)
                    self.report_preview.insert(tk.END, f"✅ Rapport PDF généré avec succès!\n\n")
                    self.report_preview.insert(tk.END, f"📁 Fichier: {report_path}\n")
                    self.report_preview.insert(tk.END, f"📊 Analyses: {len(analyses)} sites\n")
                    self.report_preview.config(state=tk.DISABLED)
                    
            else:
                messagebox.showerror("Rapport", "Format non supporté")

        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erreur", f"Erreur lors de la génération du rapport: {e}")

    def _update_report_preview(self, content, filepath, format_type):
        """Met à jour la zone d'aperçu du rapport"""
        self.report_preview.config(state=tk.NORMAL)
        self.report_preview.delete("1.0", tk.END)
        
        # Ajouter un en-tête informatif
        self.report_preview.insert(tk.END, f"✅ Rapport {format_type} généré avec succès!\n\n")
        self.report_preview.insert(tk.END, f"📁 Fichier: {filepath}\n")
        self.report_preview.insert(tk.END, f"📏 Taille: {len(content)} caractères\n\n")
        self.report_preview.insert(tk.END, "="*50 + "\n\n")
        
        # Ajouter le contenu (limité pour les gros fichiers)
        if len(content) > 10000:
            self.report_preview.insert(tk.END, content[:10000])
            self.report_preview.insert(tk.END, f"\n\n... (contenu tronqué - fichier trop volumineux)\n")
            self.report_preview.insert(tk.END, f"📏 Total: {len(content)} caractères\n")
        else:
            self.report_preview.insert(tk.END, content)
        
        self.report_preview.config(state=tk.DISABLED)

    def _open_reports_folder(self):
        """Ouvre le dossier des rapports"""
        try:
            reports_dir = os.path.abspath("reports")
            if os.path.exists(reports_dir):
                os.startfile(reports_dir)
            else:
                messagebox.showinfo("Info", "Le dossier des rapports n'existe pas encore.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir le dossier: {e}")
       
if __name__ == "__main__":
    root = tk.Tk()
    app = ModernRadarApp(root)
    root.mainloop()