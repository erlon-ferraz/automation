import os
import time
import json
import requests
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from bs4 import BeautifulSoup
import random

# --- CONFIGURAÇÕES (PREENCHA AQUI) ---
APP_ID = '5839758944487505'
CLIENT_SECRET = 'AlCmzubnNBsPRShTz1ZDHCRm79ohLOMV'

# URL do seu Backend no Render (Preencha após criar o serviço no Render)
# Ex: https://api-allpecas.onrender.com
RENDER_URL = 'https://SUA-URL-DO-RENDER.onrender.com' 

REDIRECT_URI = f'{RENDER_URL}/Automation/callback'
TOKEN_FILE = 'tokens.json'

app = Flask(__name__)
CORS(app) # Permite conexão com a Hostinger

# --- TOKEN MANAGER ---
def save_tokens(token_data):
    token_data['expires_at'] = time.time() + token_data.get('expires_in', 21600)
    with open(TOKEN_FILE, 'w') as f: json.dump(token_data, f)

def load_tokens():
    if not os.path.exists(TOKEN_FILE): return None
    try:
        with open(TOKEN_FILE, 'r') as f: return json.load(f)
    except: return None

def get_valid_token():
    tokens = load_tokens()
    if not tokens: return None
    if time.time() > (tokens.get('expires_at', 0) - 60):
        print("🔄 Token expirado! Renovando...")
        try:
            resp = requests.post('https://api.mercadolibre.com/oauth/token', data={
                'grant_type': 'refresh_token', 'client_id': APP_ID, 'client_secret': CLIENT_SECRET,
                'refresh_token': tokens['refresh_token']
            })
            resp.raise_for_status()
            new_tokens = resp.json()
            save_tokens(new_tokens)
            return new_tokens['access_token']
        except: return None
    return tokens['access_token']

def predict_category(title):
    try:
        resp = requests.get(f"https://api.mercadolibre.com/sites/MLB/domain_discovery/search?q={title}")
        return resp.json()[0].get('category_id') if resp.json() else "MLB1747"
    except: return "MLB1747"

# --- ROTAS DE LOGIN ---
@app.route('/')
def index(): return "API Online 🚀"

@app.route('/Automation/login')
def login():
    url = f"https://auth.mercadolivre.com.br/authorization?response_type=code&client_id={APP_ID}&redirect_uri={REDIRECT_URI}"
    return redirect(url)

@app.route('/Automation/callback')
def callback():
    code = request.args.get('code')
    try:
        resp = requests.post('https://api.mercadolibre.com/oauth/token', data={
            'grant_type': 'authorization_code', 'client_id': APP_ID, 'client_secret': CLIENT_SECRET,
            'code': code, 'redirect_uri': REDIRECT_URI
        })
        resp.raise_for_status()
        save_tokens(resp.json())
        # Redireciona de volta para o seu site
        return redirect('https://allpecasbrasil.com.br/Automation/')
    except Exception as e: return f"Erro login: {e}"

# --- ROTA DE BUSCA (SCRAPING) ---
@app.route('/Automation/api/scrape-search')
def api_search():
    prod = request.args.get('produto')
    marca = request.args.get('marca')
    if not prod: return jsonify({'error': 'Produto vazio'}), 400
    
    # Scraping Logic
    termo = f"{prod} {marca}".strip().replace(" ", "-")
    url = f'https://lista.mercadolivre.com.br/{termo}_OrderId_PRICE_NoIndex_True'
    ua_list = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36']
    
    try:
        resp = requests.get(url, headers={'User-Agent': random.choice(ua_list)})
        soup = BeautifulSoup(resp.content, 'html.parser')
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

                # Meta dados
                t_img = item.find('img', {'class': 'poly-component__picture'}) or item.find('img', {'class': 'ui-search-result-image__element'})
                img = t_img.get('data-src') or t_img.get('src') if t_img else ""
                
                t_brand = item.find('span', {'class': 'poly-component__brand'})
                brand = t_brand.text.strip() if t_brand else marca.upper()
                
                t_sold = item.find('span', {'class': 'poly-component__review-compacted'})
                sold = t_sold.text.strip() if t_sold and "vendido" in t_sold.text else "Novo"
                
                t_sell = item.find('span', {'class': 'poly-component__seller'})
                seller = t_sell.text.strip() if t_sell else "ML"

                if price > 0: res.append({'title': t_tit.text.strip(), 'price': price, 'permalink': t_tit.get('href'), 'img': img, 'brand': brand, 'soldQty': sold, 'seller': seller})
                if len(res) >= 10: break
            except: continue
        return jsonify({'items': res})
    except Exception as e: return jsonify({'error': str(e)}), 500

# --- ROTA DE PUBLICAR ---
@app.route('/Automation/api/publicar-anuncio', methods=['POST'])
def publicar():
    token = get_valid_token()
    if not token: return jsonify({'status': 'error', 'message': 'Faça login no ML primeiro'}), 401
    d = request.json
    
    img = d.get('imgUrl') if d.get('imgUrl') and 'http' in d.get('imgUrl') else "https://http2.mlstatic.com/frontend-assets/ui-navigation/5.19.5/mercadolibre/logo__large_plus.png"
    
    payload = {
        "title": d.get('titulo'),
        "category_id": predict_category(d.get('titulo')),
        "price": d.get('preco'),
        "currency_id": "BRL",
        "available_quantity": 1,
        "buying_mode": "buy_it_now",
        "listing_type_id": d.get('tipo'),
        "condition": "new",
        "description": {"plain_text": f"Produto: {d.get('titulo')} - Marca: {d.get('marca')}"},
        "pictures": [{"source": img}],
        "attributes": [{"id": "BRAND", "value_name": d.get('marca')}]
    }
    try:
        r = requests.post("https://api.mercadolibre.com/items", json=payload, headers={"Authorization": f"Bearer {token}"})
        if r.status_code == 201: return jsonify({'status': 'success', 'message': 'Criado!', 'link': r.json().get('permalink')})
        return jsonify({'status': 'error', 'message': r.text}), 400
    except Exception as e: return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)