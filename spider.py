from datetime import datetime, timedelta
import time
from database import App, Crawl, db, Product
from parse import Parser


def run_spider():
    while True:
        db.connect(True)
        old_crawlers = Crawl.select().where(Crawl.created_at < (datetime.now() - timedelta(days=3)))
        dq = (Product
            .delete()
            .where(Product.crawlid.in_(old_crawlers)))
        dq.execute()

        app = App.create(name='start', start_url='')
        crawl, created = Crawl.get_or_create(finished=False)

        while True:
            try:
                parser.start(app, crawl)
                break
            except Exception as e:
                print(f'Error occurred while scraping: {e}')
                time.sleep(5)
            time.sleep(60)

        db.connect(True)
        crawl.finished = True
        crawl.save()
        db.close()
        
        time.sleep(60*60)


if __name__ == '__main__':
    while True:
        parser = Parser()
        try: run_spider()
        except Exception as e: print(f'Unexpected exception occurred {e}')
        time.sleep(5)
