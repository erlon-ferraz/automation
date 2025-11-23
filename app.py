import os
import json
import requests
import random
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

# --- SCRAPING ROBUSTO ---
def realizar_scraping(produto, marca):
    termo = f"{produto} {marca}".strip().replace(" ", "-")
    # Removemos o filtro de ordenação forçada pois as vezes ele quebra a busca em IPs internacionais
    # Vamos ordenar nós mesmos no final
    url = f'https://lista.mercadolivre.com.br/{termo}'
    
    ua_list = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    ]
    
    headers = {
        'User-Agent': random.choice(ua_list),
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.mercadolivre.com.br/',
        'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'sec-ch-ua-platform': '"Windows"'
    }

    try:
        print(f"--- Iniciando busca: {url} ---")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Erro HTTP ML: {response.status_code}")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # ESTRATÉGIA MULTI-LAYOUT
        # 1. Tenta Layout Novo (Poly)
        itens = soup.find_all('div', {'class': 'poly-card'})
        
        # 2. Tenta Layout Lista Antigo
        if not itens:
            itens = soup.find_all('li', {'class': 'ui-search-layout__item'})
            
        # 3. Tenta Layout Grade
        if not itens:
            itens = soup.find_all('div', {'class': 'ui-search-result__wrapper'})

        print(f"Encontrados {len(itens)} elementos brutos.")

        resultados = []
        for item in itens:
            try:
                # TÍTULO (Tenta várias classes)
                tag_tit = item.find('a', {'class': 'poly-component__title'}) or \
                          item.find('h2', {'class': 'ui-search-item__title'}) or \
                          item.find('h2', {'class': 'poly-component__title'})
                
                if not tag_tit: continue
                titulo = tag_tit.text.strip()
                link = tag_tit.get('href')

                # PREÇO (Tenta várias estruturas)
                price = 0.0
                # Estrutura Poly
                container_poly = item.find('div', {'class': 'poly-price__current'})
                # Estrutura Antiga
                container_old = item.find('div', {'class': 'ui-search-price__second-line'})
                
                container = container_poly or container_old
                
                if container:
                    inteiro = container.find('span', {'class': 'andes-money-amount__fraction'})
                    cent = container.find('span', {'class': 'andes-money-amount__cents'})
                    if inteiro:
                        txt_price = inteiro.text.replace('.', '')
                        if cent: txt_price += f".{cent.text}"
                        price = float(txt_price)

                # IMAGEM
                tag_img = item.find('img')
                img = ""
                if tag_img:
                    img = tag_img.get('data-src') or tag_img.get('src')

                # MARCA
                brand = marca.upper() # Default
                # Tenta achar a marca no card
                tag_brand = item.find('span', {'class': 'poly-component__brand'}) or item.find('span', {'class': 'ui-search-item__brand-name'})
                if tag_brand: brand = tag_brand.text.strip()

                # VENDIDOS
                sold = "Novo"
                # Procura qualquer span que tenha a palavra "vendido"
                for span in item.find_all('span'):
                    if span.text and 'vendido' in span.text.lower():
                        sold = span.text.strip()
                        break

                # VENDEDOR
                seller = "Mercado Livre"
                tag_sell = item.find('span', {'class': 'poly-component__seller'}) or item.find('p', {'class': 'ui-search-official-store-label'})
                if tag_sell: seller = tag_sell.text.strip()

                if price > 0:
                    resultados.append({
                        'title': titulo, 
                        'price': price, 
                        'permalink': link, 
                        'img': img, 
                        'brand': brand, 
                        'soldQty': sold, 
                        'seller': seller
                    })
            except Exception as e:
                continue # Pula item com erro
        
        # ORDENAÇÃO MANUAL (Já que tiramos da URL)
        # Ordena pelo menor preço
        resultados.sort(key=lambda x: x['price'])
        
        return resultados[:15] # Retorna os 15 primeiros

    except Exception as e:
        print(f"Erro Crítico no Scraping: {e}")
        return []

# --- ROTAS ---
@app.route('/')
def index(): return "API Online 2.0 (Scraper Blindado) 🚀"

def execute_search():
    prod = request.args.get('produto')
    marca = request.args.get('marca')
    print(f"Pedido recebido: {prod} - {marca}")
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