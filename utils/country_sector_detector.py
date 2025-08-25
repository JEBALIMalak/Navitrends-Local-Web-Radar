import re
import tldextract
from bs4 import BeautifulSoup
import requests

class CountrySectorDetector:
    def __init__(self):
        # Mapping des TLDs vers les pays
        self.tld_to_country = {
            'fr': 'France', 'de': 'Germany', 'uk': 'United Kingdom', 'com': 'International',
            'org': 'International', 'net': 'International', 'it': 'Italy', 'es': 'Spain',
            'be': 'Belgium', 'ch': 'Switzerland', 'ca': 'Canada', 'us': 'United States',
            'au': 'Australia', 'jp': 'Japan', 'cn': 'China', 'ru': 'Russia', 'br': 'Brazil',
            'nl': 'Netherlands', 'se': 'Sweden', 'no': 'Norway', 'dk': 'Denmark'
        }
        
        # Mots-clés par secteur d'activité
        self.sector_keywords = {
            'technologie': ['tech', 'software', 'it', 'computer', 'digital', 'web', 'app', 'cloud'],
            'sante': ['health', 'medical', 'hospital', 'pharma', 'care', 'clinique', 'médecin'],
            'finance': ['bank', 'finance', 'insurance', 'investment', 'credit', 'loan', 'money'],
            'education': ['education', 'school', 'university', 'college', 'learn', 'course'],
            'commerce': ['shop', 'store', 'ecommerce', 'buy', 'sell', 'market', 'retail'],
            'restauration': ['restaurant', 'food', 'cafe', 'bistro', 'meal', 'cuisine'],
            'immobilier': ['real estate', 'property', 'house', 'apartment', 'rent', 'buy'],
            'tourisme': ['travel', 'tour', 'hotel', 'vacation', 'trip', 'destination']
        }

    def detect_country(self, url, html_content=None):
        """Détecte le pays basé sur le domaine et le contenu"""
        try:
            # Extraction du TLD
            extracted = tldextract.extract(url)
            tld = extracted.suffix
            
            # Vérification du TLD country code
            if '.' in tld:
                country_tld = tld.split('.')[-1]
                if country_tld in self.tld_to_country:
                    return self.tld_to_country[country_tld]
            
            # Vérification du TLD simple
            if tld in self.tld_to_country:
                return self.tld_to_country[tld]
            
            # Analyse du contenu HTML pour les indices de pays
            if html_content:
                soup = BeautifulSoup(html_content, 'html.parser')
                text = soup.get_text().lower()
                
                # Recherche de mentions de pays dans le texte
                country_indicators = {
                    'france': ['france', 'français', 'paris', 'euro', '€'],
                    'germany': ['germany', 'deutschland', 'berlin', 'euro', '€'],
                    'united kingdom': ['uk', 'united kingdom', 'london', 'pound', '£'],
                    'united states': ['usa', 'united states', 'new york', 'dollar', '$'],
                    'canada': ['canada', 'toronto', 'cad', 'dollar', '$']
                }
                
                for country, indicators in country_indicators.items():
                    for indicator in indicators:
                        if indicator in text:
                            return country
            
            return 'International'
            
        except Exception as e:
            print(f"Erreur dans la détection du pays: {e}")
            return 'Unknown'

    def detect_sector(self, url, html_content=None):
        """Détecte le secteur d'activité basé sur l'URL et le contenu"""
        try:
            # Analyse de l'URL
            domain = url.lower()
            for sector, keywords in self.sector_keywords.items():
                for keyword in keywords:
                    if keyword in domain:
                        return sector
            
            # Analyse du contenu HTML si disponible
            if html_content:
                soup = BeautifulSoup(html_content, 'html.parser')
                text = soup.get_text().lower()
                
                # Recherche des mots-clés dans le contenu
                sector_counts = {}
                for sector, keywords in self.sector_keywords.items():
                    count = 0
                    for keyword in keywords:
                        count += text.count(keyword)
                    if count > 0:
                        sector_counts[sector] = count
                
                # Retourne le secteur avec le plus d'occurrences
                if sector_counts:
                    return max(sector_counts.items(), key=lambda x: x[1])[0]
            
            # Analyse des meta tags
            if html_content:
                soup = BeautifulSoup(html_content, 'html.parser')
                meta_description = soup.find('meta', attrs={'name': 'description'})
                if meta_description:
                    desc = meta_description.get('content', '').lower()
                    for sector, keywords in self.sector_keywords.items():
                        for keyword in keywords:
                            if keyword in desc:
                                return sector
            
            return 'general'
            
        except Exception as e:
            print(f"Erreur dans la détection du secteur: {e}")
            return 'unknown'

# Test de la classe
if __name__ == "__main__":
    detector = CountrySectorDetector()
    
    # Test avec quelques URLs
    test_urls = [
        "https://www.amazon.fr",
        "https://www.microsoft.com",
        "https://www.santefrance.fr",
        "https://www.bbva.es"
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            country = detector.detect_country(url, response.text)
            sector = detector.detect_sector(url, response.text)
            print(f"{url} -> Pays: {country}, Secteur: {sector}")
        except:
            country = detector.detect_country(url)
            sector = detector.detect_sector(url)
            print(f"{url} -> Pays: {country}, Secteur: {sector} (sans contenu)")