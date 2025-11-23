import os
import json
import requests
import random
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from flask_cors import CORS  # <--- ISSO É O SEGREDO

app = Flask(__name__)
# Permite que a Hostinger acesse este Python
CORS(app) 

# --- SEU SCRAPER ORIGINAL (MANTIDO) ---
def realizar_scraping(produto, marca):
    termo = f"{produto} {marca}".strip().replace(" ", "-")
    # A URL mágica que você descobriu
    url = f'https://lista.mercadolivre.com.br/{termo}_OrderId_PRICE_NoIndex_True'
    
    ua_list = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    ]
    
    headers = {
        'User-Agent': random.choice(ua_list),
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.mercadolivre.com.br/'
    }

    try:
        print(f"Buscando: {url}")
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Tenta os dois layouts do ML
        itens = soup.find_all('li', {'class': 'ui-search-layout__item'})
        if not itens: itens = soup.find_all('div', {'class': 'poly-card'})

        resultados = []
        for item in itens:
            try:
                # Título
                t_tit = item.find('a', {'class': 'poly-component__title'}) or item.find('h2', {'class': 'ui-search-item__title'})
                if not t_tit: continue
                titulo = t_tit.text.strip()
                link = t_tit.get('href')

                # Preço
                price = 0.0
                c_pr = item.find('div', {'class': 'poly-price__current'}) or item.find('div', {'class': 'ui-search-price__second-line'})
                if c_pr:
                    inteiro = c_pr.find('span', {'class': 'andes-money-amount__fraction'})
                    cent = c_pr.find('span', {'class': 'andes-money-amount__cents'})
                    if inteiro:
                        price = float(inteiro.text.replace('.','') + (f".{cent.text}" if cent else ""))

                # Meta dados
                t_img = item.find('img', {'class': 'poly-component__picture'}) or item.find('img', {'class': 'ui-search-result-image__element'})
                img = t_img.get('data-src') or t_img.get('src') if t_img else ""
                
                t_brand = item.find('span', {'class': 'poly-component__brand'})
                brand = t_brand.text.strip() if t_brand else marca.upper()
                
                t_sold = item.find('span', {'class': 'poly-component__review-compacted'})
                sold = t_sold.text.strip() if t_sold and "vendido" in t_sold.text else "Novo"
                
                t_sell = item.find('span', {'class': 'poly-component__seller'})
                seller = t_sell.text.strip() if t_sell else "Mercado Livre"

                if price > 0:
                    resultados.append({
                        'title': titulo, 'price': price, 'permalink': link, 
                        'img': img, 'brand': brand, 'soldQty': sold, 'seller': seller
                    })
                if len(resultados) >= 10: break
            except: continue
            
        return resultados
    except Exception as e:
        print(f"Erro no scraping: {e}")
        return []

# --- ROTAS ---

@app.route('/')
def index():
    return "API All Peças Rodando! 🚀"

# Rota simplificada para evitar confusão
@app.route('/api/busca', methods=['GET'])
def api_busca():
    prod = request.args.get('produto')
    marca = request.args.get('marca')
    
    if not prod: return jsonify({'error': 'Faltou o produto'}), 400
    
    items = realizar_scraping(prod, marca)
    return jsonify({'items': items})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)