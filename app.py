import os
import random
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from flask_cors import CORS # Importante

app = Flask(__name__)

# --- CORREÇÃO DO CORS ---
# Isso libera geral. O navegador vai parar de reclamar.
CORS(app, resources={r"/*": {"origins": "*"}})

# --- SEU SCRAPER (MANTIDO IGUAL) ---
def realizar_scraping(produto, marca):
    termo = f"{produto} {marca}".strip().replace(" ", "-")
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
        print(f"Buscando no ML: {url}") # Log para ver no painel do Render
        response = requests.get(url, headers=headers)
        # Se o ML bloquear (403/429), não quebra o server, retorna lista vazia
        if response.status_code != 200:
            print(f"Bloqueio ML: {response.status_code}")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')
        
        itens = soup.find_all('li', {'class': 'ui-search-layout__item'})
        if not itens: itens = soup.find_all('div', {'class': 'poly-card'})

        resultados = []
        for item in itens:
            try:
                # Título
                t_tit = item.find('a', {'class': 'poly-component__title'}) or item.find('h2', {'class': 'ui-search-item__title'}) or item.find('a', {'class': 'ui-search-item__group__element'})
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
                        texto_preco = inteiro.text.replace('.', '')
                        if cent: texto_preco += f".{cent.text}"
                        price = float(texto_preco)

                # Imagem
                t_img = item.find('img', {'class': 'poly-component__picture'}) or item.find('img', {'class': 'ui-search-result-image__element'})
                img = t_img.get('data-src') or t_img.get('src') if t_img else ""
                
                # Marca
                t_brand = item.find('span', {'class': 'poly-component__brand'})
                brand = t_brand.text.strip() if t_brand else marca.upper()
                
                # Vendidos
                sold = "Novo"
                t_sold = item.find('span', {'class': 'poly-component__review-compacted'})
                if t_sold and "vendido" in t_sold.text.lower(): sold = t_sold.text.strip()
                
                # Vendedor
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
        print(f"Erro Crítico: {e}")
        return []

# --- ROTAS ---

@app.route('/')
def health_check():
    return "API Online e Funcionando! ✅"

# Essa é a rota exata que seu JS está chamando
@app.route('/api/busca', methods=['GET'])
def api_busca():
    prod = request.args.get('produto')
    marca = request.args.get('marca')
    
    print(f"Recebido pedido: {prod} - {marca}") # Log para debug
    
    if not prod: 
        return jsonify({'error': 'Faltou o produto'}), 400
    
    items = realizar_scraping(prod, marca)
    
    # Retorna JSON com cabeçalho CORS explícito (segurança extra)
    response = jsonify({'items': items})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

if __name__ == '__main__':
    # Configuração para rodar no Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)