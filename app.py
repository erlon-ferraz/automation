import os
import time
import json
import requests
import random
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS

# --- CONFIGURAÇÕES ---
APP_ID = '5839758944487505'          # <--- Preencha se for publicar
CLIENT_SECRET = 'AlCmzubnNBsPRShTz1ZDHCRm79ohLOMV' # <--- Preencha se for publicar
TOKEN_FILE = 'tokens.json'

# URL do seu Backend no Render
RENDER_URL = 'https://automation-fcdt.onrender.com' 
REDIRECT_URI = f'{RENDER_URL}/Automation/callback'

app = Flask(__name__)
# Libera o CORS para qualquer origem (resolve o erro de bloqueio)
CORS(app, resources={r"/*": {"origins": "*"}})

# --- SCRAPING (Lógica de Busca) ---
def realizar_scraping(produto, marca):
    termo = f"{produto} {marca}".strip().replace(" ", "-")
    url = f'https://lista.mercadolivre.com.br/{termo}_OrderId_PRICE_NoIndex_True'
    
    ua_list = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    ]
    
    try:
        print(f"Buscando: {url}")
        response = requests.get(url, headers={'User-Agent': random.choice(ua_list), 'Referer': 'https://mercadolivre.com.br'})
        
        if response.status_code != 200: return []

        soup = BeautifulSoup(response.content, 'html.parser')
        itens = soup.find_all('li', {'class': 'ui-search-layout__item'}) or soup.find_all('div', {'class': 'poly-card'})
        
        res = []
        for item in itens:
            try:
                t_tit = item.find('a', {'class': 'poly-component__title'}) or item.find('h2', {'class': 'ui-search-item__title'})
                if not t_tit: continue
                
                # Preço
                price = 0.0
                c_pr = item.find('div', {'class': 'poly-price__current'}) or item.find('div', {'class': 'ui-search-price__second-line'})
                if c_pr:
                    inteiro = c_pr.find('span', {'class': 'andes-money-amount__fraction'})
                    cent = c_pr.find('span', {'class': 'andes-money-amount__cents'})
                    if inteiro: price = float(inteiro.text.replace('.','') + (f".{cent.text}" if cent else ""))

                # Img
                t_img = item.find('img', {'class': 'poly-component__picture'}) or item.find('img', {'class': 'ui-search-result-image__element'})
                img = t_img.get('data-src') or t_img.get('src') if t_img else ""
                
                # Brand/Sold
                brand = marca.upper()
                t_br = item.find('span', {'class': 'poly-component__brand'})
                if t_br: brand = t_br.text.strip()
                
                sold = "Novo"
                t_sold = item.find('span', {'class': 'poly-component__review-compacted'})
                if t_sold and "vendido" in t_sold.text: sold = t_sold.text.strip()
                
                t_sell = item.find('span', {'class': 'poly-component__seller'})
                seller = t_sell.text.strip() if t_sell else "ML"

                if price > 0: res.append({'title': t_tit.text.strip(), 'price': price, 'permalink': t_tit.get('href'), 'img': img, 'brand': brand, 'soldQty': sold, 'seller': seller})
                if len(res) >= 10: break
            except: continue
        return res
    except Exception as e:
        print(f"Erro scraping: {e}")
        return []

# --- ROTAS (UNIVERSAIS) ---
# Aqui definimos a rota COM e SEM o prefixo /Automation para garantir que funcione

@app.route('/')
def home(): return "API Online! ✅"

# Rota 1: Caminho completo (que seu JS está pedindo)
@app.route('/Automation/api/scrape-search')
def search_full():
    return execute_search()

# Rota 2: Caminho curto (caso mude o JS)
@app.route('/api/scrape-search')
def search_short():
    return execute_search()

def execute_search():
    prod = request.args.get('produto')
    marca = request.args.get('marca')
    if not prod: return jsonify({'error': 'Faltou produto'}), 400
    items = realizar_scraping(prod, marca)
    return jsonify({'items': items})

# --- ROTA DE PUBLICAR (Também duplicada por segurança) ---
@app.route('/Automation/api/publicar-anuncio', methods=['POST'])
def pub_full(): return publicar_logica()

@app.route('/api/publicar-anuncio', methods=['POST'])
def pub_short(): return publicar_logica()

def publicar_logica():
    # (Sua lógica de token e publicação entra aqui)
    # Por enquanto retorna sucesso simulado para teste
    return jsonify({'status': 'success', 'message': 'Rota de publicação conectada! Falta configurar Token.'})

# --- TOKEN MANAGER (Rotas) ---
@app.route('/Automation/login')
def login():
    url = f"https://auth.mercadolivre.com.br/authorization?response_type=code&client_id={APP_ID}&redirect_uri={REDIRECT_URI}"
    return redirect(url)

@app.route('/Automation/callback')
def callback():
    # Lógica de salvar token...
    return redirect('https://allpecasbrasil.com.br/Automation/')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)