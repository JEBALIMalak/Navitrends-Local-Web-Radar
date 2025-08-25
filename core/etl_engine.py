import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time
import json
import re
from datetime import datetime
import logging

from utils.country_sector_detector import CountrySectorDetector

logger = logging.getLogger(__name__)

class WebRadarETL:
    def __init__(self, config_path='config.json'):
        # Configuration par défaut
        default_config = {
            "timeout": 30,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "google_api_key": "zaSyCmXDxj0uo4dJGXRxOPAGvLw_Vf87avW5U",
            "max_retries": 2,
            "retry_delay": 1
        }
        
        # Essayer de charger la config, sinon utiliser les valeurs par défaut
        try:
            with open(config_path, 'r') as f:
                content = f.read().strip()
                if content:
                    self.config = json.loads(content)
                    print("✅ Configuration chargée depuis config.json")
                else:
                    raise ValueError("Fichier config vide")
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            print(f"⚠️  Erreur de configuration: {e}. Utilisation des valeurs par défaut.")
            self.config = default_config
            # Sauvegarder la config par défaut
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            print("✅ Configuration par défaut sauvegardée")
        
        self.detector = CountrySectorDetector()
        logger.info("Configuration chargée")

    def is_valid_url(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def extract(self, url):
        retries = self.config.get('max_retries', 2)
        for attempt in range(retries):
            try:
                response = requests.get(url, timeout=self.config['timeout'],
                                        headers={'User-Agent': self.config['user_agent']})
                return {
                    'url': url,
                    'html': response.text,
                    'status': response.status_code,
                    'headers': dict(response.headers)
                }
            except Exception as e:
                logger.error(f"Tentative {attempt+1} échouée pour {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(self.config.get('retry_delay', 1))
                else:
                    return {'url': url, 'error': str(e)}

    def transform(self, data, country_filter=None, sector_filter=None):
        if 'error' in data:
            return data

        analysis = {'url': data['url'], 'status': data['status']}
        soup = BeautifulSoup(data['html'], 'html.parser')

        # Détection pays et secteur
        analysis['country'] = self.detector.detect_country(data['url'], data['html'])
        analysis['sector'] = self.detector.detect_sector(data['url'], data['html'])
        
        # CORRECTION: Gestion des filtres "Tous" et valeurs None
        if country_filter and country_filter != "Tous" and analysis['country'] != country_filter:
            return {'url': data['url'], 'error': 'Filtre pays non respecté', 'filtered': True, 'country': analysis['country']}
            
        if sector_filter and sector_filter != "Tous" and analysis['sector'] != sector_filter:
            return {'url': data['url'], 'error': 'Filtre secteur non respecté', 'filtered': True, 'sector': analysis['sector']}

        # HTTPS
        parsed = urlparse(data['url'])
        analysis['https'] = parsed.scheme == 'https'

        # Title
        title = soup.title.string if soup.title else ''
        analysis['title'] = {
            'exists': bool(title),
            'content': title,
            'length': len(title),
            'optimal': 30 <= len(title) <= 60
        }

        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        desc_content = meta_desc.get('content') if meta_desc else ''
        analysis['meta_description'] = {
            'exists': bool(meta_desc),
            'content': desc_content,
            'length': len(desc_content),
            'optimal': 150 <= len(desc_content) <= 160
        }

        # H1
        h1_tags = soup.find_all('h1')
        analysis['h1'] = {
            'count': len(h1_tags),
            'contents': [h.get_text().strip() for h in h1_tags],
            'optimal': len(h1_tags) == 1
        }

        # Images sans alt text
        images = soup.find_all('img')
        images_without_alt = [img for img in images if not img.get('alt')]
        analysis['images'] = {
            'total': len(images),
            'without_alt': len(images_without_alt),
            'optimal': len(images_without_alt) == 0
        }

        # Liens internes et externes
        all_links = soup.find_all('a', href=True)
        internal_links = []
        external_links = []
        
        domain = parsed.netloc
        for link in all_links:
            href = link['href']
            if href.startswith('http') or href.startswith('//'):
                if domain in href:
                    internal_links.append(href)
                else:
                    external_links.append(href)
            else:
                internal_links.append(href)
                
        analysis['links'] = {
            'total': len(all_links),
            'internal': len(internal_links),
            'external': len(external_links)
        }

        # Taille de la page
        analysis['page_size'] = len(data['html'].encode('utf-8'))

        # Détection CMS
        analysis['cms'] = self.detect_cms(soup, data['headers'])

        # Performance
        analysis['performance'] = self.measure_performance(data['url'])

        # Copyright
        analysis['copyright'] = self.detect_copyright_year(soup)

        # Mobile-friendly test
        analysis['mobile'] = self.mobile_friendly_test(data['url'])

        # Calcul du score - CORRECTION: Gestion des valeurs manquantes
        score = 100
        
        # Vérifications sécurisées avec .get() pour éviter KeyError
        if not analysis.get('https', True): 
            score -= 15
        
        title_data = analysis.get('title', {})
        if not title_data.get('exists') or not title_data.get('optimal', True):
            score -= 10
        
        meta_data = analysis.get('meta_description', {})
        if not meta_data.get('exists') or not meta_data.get('optimal', True):
            score -= 5
        
        h1_data = analysis.get('h1', {})
        if not h1_data.get('optimal', True):
            score -= 5
        
        images_data = analysis.get('images', {})
        if not images_data.get('optimal', True):
            score -= 5
        
        mobile_data = analysis.get('mobile', {})
        if not mobile_data.get('mobileFriendly', True):
            score -= 15
        
        perf_data = analysis.get('performance', {})
        if perf_data.get('slow', False):
            score -= 10
        
        cms_data = analysis.get('cms', {})
        if cms_data.get('outdated', False):
            score -= 10
        
        copyright_data = analysis.get('copyright', {})
        if copyright_data.get('outdated', False):
            score -= 5
        
        if analysis.get('page_size', 0) > 2000000:
            score -= 5
        
        analysis['score'] = max(0, min(score, 100))  # Score entre 0 et 100

        return analysis
    def load(self, analysis):
        issues = []
        if 'error' in analysis:
            if analysis.get('filtered'):
                return None  # Ignorer les résultats filtrés
            issues.append(f"❌ Erreur: {analysis['error']}")
            return {'url': analysis['url'], 'issues': issues, 'score': 0, 'details': analysis}

        if not analysis['https']:
            issues.append("🔒 Pas de HTTPS")
        if not analysis['title']['exists']:
            issues.append("💡 Pas de <title>")
        elif not analysis['title']['optimal']:
            issues.append("📏 Titre non optimal")
        if not analysis['meta_description']['exists']:
            issues.append("📝 Pas de meta description")
        elif not analysis['meta_description']['optimal']:
            issues.append("📐 Meta description non optimale")
        if not analysis['h1']['optimal']:
            issues.append(f"🔤 H1 count: {analysis['h1']['count']}")
        if not analysis['images']['optimal']:
            issues.append(f"🖼️ Images sans alt: {analysis['images']['without_alt']}")
        if not analysis['mobile'].get('mobileFriendly', True):
            issues.append("📱 Non mobile-friendly")
        if analysis['performance'].get('slow', False):
            issues.append(f"🐌 Temps de chargement lent: {analysis['performance']['load_time']}s")
        if analysis['cms'].get('outdated', False):
            issues.append(f"🧱 CMS obsolète: {analysis['cms']['name']} {analysis['cms']['version']}")
        if analysis['copyright'].get('outdated', False):
            issues.append(f"📅 Copyright ancien: {analysis['copyright']['year']}")
        if analysis['page_size'] > 2000000:
            issues.append(f"⚖️ Page trop lourde: {analysis['page_size']/1024:.1f} KB")

        return {
            'url': analysis['url'], 
            'issues': issues, 
            'score': analysis['score'], 
            'details': analysis,
            'country': analysis.get('country', 'Inconnu'),
            'sector': analysis.get('sector', 'Inconnu')
        }

    def detect_cms(self, soup, headers):
        """Détecte le CMS utilisé par le site"""
        cms = "Inconnu"
        version = "N/A"
        
        # Détection par meta generator
        meta_generator = soup.find('meta', attrs={'name': 'generator'})
        if meta_generator:
            content = meta_generator.get('content', '').lower()
            if 'wordpress' in content:
                cms = "WordPress"
                version_match = re.search(r'wordpress\s*(\d+\.\d+(\.\d+)?)', content)
                if version_match:
                    version = version_match.group(1)
            elif 'joomla' in content:
                cms = "Joomla"
                version_match = re.search(r'joomla\s*(\d+\.\d+(\.\d+)?)', content)
                if version_match:
                    version = version_match.group(1)
            elif 'drupal' in content:
                cms = "Drupal"
                version_match = re.search(r'drupal\s*(\d+\.\d+(\.\d+)?)', content)
                if version_match:
                    version = version_match.group(1)
        
        # Détection par classes CSS
        if cms == "Inconnu":
            if soup.find('body', class_=lambda x: x and 'wp-admin' in x) or soup.find('div', id='wpadminbar'):
                cms = "WordPress"
            elif soup.find('body', class_=lambda x: x and 'joomla' in x):
                cms = "Joomla"
            elif soup.find('body', class_=lambda x: x and 'drupal' in x):
                cms = "Drupal"
        
        # Vérifier si le CMS est obsolète
        outdated = self._is_cms_outdated(cms, version)
        
        return {'name': cms, 'version': version, 'outdated': outdated}

    def _is_cms_outdated(self, cms, version):
        """Vérifie si la version du CMS est obsolète"""
        if cms == "Inconnu" or version == "N/A":
            return False
            
        try:
            # Versions minimales recommandées
            min_versions = {
                "WordPress": "5.0",
                "Joomla": "3.9",
                "Drupal": "8.0"
            }
            
            if cms not in min_versions:
                return False
                
            # Comparaison des versions
            from packaging import version as pkg_version
            return pkg_version.parse(version) < pkg_version.parse(min_versions[cms])
        except:
            return False

    def measure_performance(self, url):
        """Mesure le temps de chargement de la page"""
        try:
            start_time = time.time()
            response = requests.get(url, timeout=self.config['timeout'], 
                                   headers={'User-Agent': self.config['user_agent']})
            load_time = time.time() - start_time
            
            return {
                'load_time': round(load_time, 2),
                'slow': load_time > 3  # > 3 secondes est considéré comme lent
            }
        except:
            return {'load_time': None, 'slow': False}

    def detect_copyright_year(self, soup):
        """Détecte l'année de copyright dans le pied de page"""
        current_year = datetime.now().year
        copyright_text = ""
        
        # Chercher dans le footer
        footer = soup.find('footer') or soup.find('div', class_=lambda x: x and 'footer' in x.lower()) or soup.find('div', id=lambda x: x and 'footer' in x.lower())
        
        if footer:
            copyright_patterns = [
                r'copyright\s*©?\s*(\d{4})', 
                r'©\s*(\d{4})', 
                r'&copy;\s*(\d{4})', 
                r'(\d{4})\s*©',
                r'copyright.*?(\d{4})'
            ]
            
            text = footer.get_text().lower()
            
            for pattern in copyright_patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        copyright_year = int(match.group(1))
                        return {
                            'year': copyright_year, 
                            'outdated': copyright_year < current_year - 2  # > 2 ans est considéré comme ancien
                        }
                    except:
                        continue
        
        return {'year': None, 'outdated': False}

    def mobile_friendly_test(self, url):
        api_key = self.config.get("google_api_key")
        if not api_key:
            return {'mobileFriendly': True}  # Simulation gratuite
        try:
            endpoint = "https://searchconsole.googleapis.com/v1/urlTestingTools/mobileFriendlyTest:run"
            resp = requests.post(f"{endpoint}?key={api_key}", json={"url": url})
            data = resp.json()
            return {'mobileFriendly': data.get('mobileFriendliness') == 'MOBILE_FRIENDLY'}
        except:
            return {'mobileFriendly': True}

    def process_site(self, url, country_filter=None, sector_filter=None):
        if not self.is_valid_url(url):
            return {'url': url, 'error': 'URL invalide', 'score': 0}
            
        extracted = self.extract(url)
        transformed = self.transform(extracted, country_filter, sector_filter)
        
        if 'error' in transformed and transformed.get('filtered'):
            return transformed  # Retourner les résultats filtrés pour le logging
            
        loaded = self.load(transformed)
        return loaded