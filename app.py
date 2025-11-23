import os
import json
import cloudscraper # <--- A Nova Biblioteca
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS

# --- CONFIGURAÇÕES ---
APP_ID = '5839758944487505'
CLIENT_SECRET = 'AlCmzubnNBsPRShTz1ZDHCRm79ohLOMV'
TOKEN_FILE = 'tokens.json'
RENDER_URL = 'https://automation-fcdt.onrender.com' 
REDIRECT_URI = f'{RENDER_URL}/Automation/callback'

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# --- SCRAPING BLINDADO (CloudScraper) ---
def realizar_scraping(produto, marca):
    termo = f"{produto} {marca}".strip().replace(" ", "-")
    url = f'https://lista.mercadolivre.com.br/{termo}'
    
    # Cria um scraper que simula um Chrome real
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    try:
        print(f"--- Tentando acessar: {url} ---")
        
        # Usa o scraper em vez do requests puro
        response = scraper.get(url)
        
        if response.status_code != 200:
            print(f"Bloqueio ou Erro: {response.status_code}")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Tenta encontrar containers de produtos (vários layouts possíveis)
        itens = soup.find_all('div', {'class': 'poly-card'})
        if not itens: itens = soup.find_all('li', {'class': 'ui-search-layout__item'})
        if not itens: itens = soup.find_all('div', {'class': 'ui-search-result__wrapper'}) # Layout antigo grid

        print(f"Encontrados {len(itens)} itens no HTML.")

        resultados = []
        for item in itens:
            try:
                # TÍTULO
                tag_tit = item.find('a', {'class': 'poly-component__title'}) or \
                          item.find('h2', {'class': 'poly-component__title'}) or \
                          item.find('h2', {'class': 'ui-search-item__title'}) or \
                          item.find('a', {'class': 'ui-search-item__group__element'})
                
                if not tag_tit: continue
                titulo = tag_tit.text.strip()
                link = tag_tit.get('href')

                # PREÇO
                price = 0.0
                # Seletores de preço
                container_price = item.find('div', {'class': 'poly-price__current'}) or \
                                  item.find('div', {'class': 'ui-search-price__second-line'}) or \
                                  item.find('div', {'class': 'ui-search-result__content-columns'})

                if container_price:
                    inteiro = container_price.find('span', {'class': 'andes-money-amount__fraction'})
                    cent = container_price.find('span', {'class': 'andes-money-amount__cents'})
                    if inteiro:
                        txt_p = inteiro.text.replace('.', '')
                        if cent: txt_p += f".{cent.text}"
                        price = float(txt_p)

                # IMAGEM
                tag_img = item.find('img')
                img = ""
                if tag_img:
                    img = tag_img.get('data-src') or tag_img.get('src')

                # META DADOS
                brand = marca.upper()
                # Tenta achar marca no HTML
                tag_brand = item.find('span', {'class': 'poly-component__brand'}) or item.find('span', {'class': 'ui-search-item__brand-name'})
                if tag_brand: brand = tag_brand.text.strip()

                sold = "Novo"
                # Busca genérica por texto 'vendido'
                for span in item.find_all('span'):
                    if span.text and 'vendido' in span.text.lower():
                        sold = span.text.strip()
                        break
                
                seller = "Mercado Livre"
                tag_sell = item.find('span', {'class': 'poly-component__seller'}) or item.find('p', {'class': 'ui-search-official-store-label'})
                if tag_sell: seller = tag_sell.text.strip()

                if price > 0:
                    resultados.append({
                        'title': titulo, 'price': price, 'permalink': link, 
                        'img': img, 'brand': brand, 'soldQty': sold, 'seller': seller
                    })
            except: continue
        
        # Ordena pelo menor preço antes de entregar
        resultados.sort(key=lambda x: x['price'])
        return resultados[:15]

    except Exception as e:
        print(f"Erro Geral: {e}")
        return []

# --- ROTAS ---
@app.route('/')
def index(): return "API CloudScraper Online 🛡️"

def execute_search():
    prod = request.args.get('produto')
    marca = request.args.get('marca')
    if not prod: return jsonify({'error': 'Faltou produto'}), 400
    items = realizar_scraping(prod, marca)
    return jsonify({'items': items})

@app.route('/Automation/api/scrape-search')
def search_full(): return execute_search()

@app.route('/api/scrape-search')
def search_short(): return execute_search()

# Rota de Publicar (Stub)
@app.route('/Automation/api/publicar-anuncio', methods=['POST'])
def publicar(): return jsonify({'status': 'success', 'message': 'Função publicar conectada!'})

# Rota Login (Stub)
@app.route('/Automation/login')
def login(): return redirect("https://www.mercadolivre.com.br") 

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)