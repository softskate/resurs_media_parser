import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from database import Product
from keys import cookie


class Parser(requests.Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers.update({
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip',
            'accept-language': 'en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7',
            'cache-control': 'max-age=0',
            'connection': 'keep-alive',
            'cookie': cookie,
            'dnt': '1',
            'host': 'b2b.resurs-media.ru',
            'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
        })


    def parse_products(self, products, cat_name, appid, crawlid):
        for prod in products.values():
            url = prod.get('fullLink', '')
            try:
                images = prod.get('files')
                if images: images = ['https://static.resurs-media.ru/images/catalog/' + x for x in images[0]]
                else: images = ['https://static.resurs-media.ru/img/no_image.png']
                brand = prod.get('manufacturer_Name')
                prod_id = prod['Nomencl_ID']
                name = prod['Name']
                price = int(prod['Price_ValueRUR'])
                qty = prod['Qty']

                details = {}
                if 'parametr' in prod:
                    details.update(prod['parametr'].get('Основные параметры', {}))
                
                details['Артикул производителя'] = prod['Nomencl_Articul_Proizvod']
                details['Склад'] = prod['Warehouse_Descr']
                details['В наличии'] = prod.get('Nalichie', '0')

                item = {}
                item['appid'] = appid
                item['crawlid'] = crawlid
                item['productId'] = prod_id
                item['name'] = name
                item['price'] = price
                item['qty'] = qty
                item['category'] = cat_name
                item['imageUrls'] = images
                item['brandName'] = brand
                item['details'] = details
                Product.create(**item)
            except Exception as e:
                print(f'Error parsing product: {url}, {e}')


    def parse(self, cat_name, url, appid, crawlid):
        soup = self.make_get('https://b2b.resurs-media.ru'+url)
        datas = soup.find_all('script')

        for data in datas:
            data = data.get_text(strip=True)
            if data.startswith('var __initialState__'):
                break

        data = data.split('=', 1)[1]
        data = data.split('var _menu', 1)[0]
        data = data.strip().strip(';')
        js_data = json.loads(data)
        prods = js_data['dataitems']['items']
        self.parse_products(prods, cat_name, appid, crawlid)

        total = js_data['pager']['totRows']
        limit = js_data['pager']['recNum']
        offset = limit
        while offset < total:
            pl = {
                'REQUEST_URI': f'{url}?curPos={offset}&recNum={limit}',
                'controller': 'CContentLoader'
            }
            resp = self.make_post('https://b2b.resurs-media.ru/netcat/modules/netshop/post.php', pl)
            prods = resp['content']['dataitems']['items']
            self.parse_products(prods, cat_name, appid, crawlid)
            offset += limit


    def make_post(self, url, data):
        print('POST', '->', url, urlencode(data))
        self.headers.update({'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'})
        resp = self.post(url, data=urlencode(data))
        return resp.json()

    def make_get(self, url, **kwargs):
        resp = self.get(url, **kwargs)
        soup = BeautifulSoup(resp.content, 'html.parser')
        return soup


    def start(self, appid, crawlid):
        soup = self.make_get('https://b2b.resurs-media.ru/')
        datas = soup.find_all('script', {'type': 'text/javascript'})

        for data in datas:
            data = data.get_text(strip=True)
            if data[:13] == '_tree_catalog':
                break

        def parse_cat(cat, parent):
            name = cat['SN']
            url = cat['U']
            child = cat['c']
            if parent: name = parent + ' - ' + name
            if child:
                for c in child.values():
                    parse_cat(c, name)

            else:
                self.parse(name, url, appid, crawlid)


        js_data = json.loads(data.split('=', 1)[1])
        for cat in js_data['333']['c'].values():
            parse_cat(cat, None)

