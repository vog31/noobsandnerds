import base64
import re
import urllib
import urlparse

from BeautifulSoup import BeautifulSoup
from nanscrapers import proxy
from nanscrapers.common import clean_title, replaceHTMLCodes
from nanscrapers.scraper import Scraper


class Primewire(Scraper):
    domains = ['primewire.ag']
    name = "primewire"

    def __init__(self):
        self.base_link = 'http://www.primewire.ag'
        self.search_link = 'http://www.primewire.ag/index.php?search'
        self.moviesearch_link = '/index.php?search_keywords=%s&key=%s&search_section=1'
        self.tvsearch_link = '/index.php?search_keywords=%s&key=%s&search_section=2'

    def scrape_movie(self, title, year, imdb):
        try:
            html = BeautifulSoup(self.get_html(title, self.moviesearch_link))
            index_items = html.findAll('div', attrs={'class': 'index_item index_item_ie'})
            title = 'watch' + clean_title(title)
            years = ['(%s)' % str(year), '(%s)' % str(int(year) + 1), '(%s)' % str(int(year) - 1)]

            for index_item in index_items:
                try:
                    links = index_item.findAll('a')
                    for link in links:
                        href = link['href']
                        link_title = link['title']

                        if any(x in link_title for x in years):
                            try:
                                href = urlparse.parse_qs(urlparse.urlparse(href).query)['u'][0]
                            except:
                                pass
                            try:
                                href = urlparse.parse_qs(urlparse.urlparse(href).query)['q'][0]
                            except:
                                pass

                            if title.lower() == clean_title(link_title) and '(%s)' % str(year) in link_title:
                                return self.sources(href)
                except:
                    continue
        except:
            pass
        return []

    def scrape_episode(self, title, year, season, episode, imdb, tvdb):
        try:
            html = BeautifulSoup(self.get_html(title, self.tvsearch_link))
            index_items = html.findAll('div', attrs={'class': re.compile('index_item.+?')})
            title = 'watch' + clean_title(title)

            for index_item in index_items:
                links = index_item.findAll('a')
                for link in links:
                    href = link['href']
                    link_title = link['title']
                    try:
                        href = urlparse.parse_qs(urlparse.urlparse(href).query)['u'][0]
                    except:
                        pass
                    try:
                        href = urlparse.parse_qs(urlparse.urlparse(href).query)['q'][0]
                    except:
                        pass

                    if title == clean_title(link_title):  # href is the show page relative url
                        show_url = urlparse.urljoin(self.base_link, href)
                        html = BeautifulSoup(proxy.get(show_url, 'tv_episode_item'))

                        seasons = html.findAll('div', attrs={'class': 'show_season'})
                        for scraped_season in seasons:
                            if scraped_season['data-id'] == season:
                                tv_episode_items = scraped_season.findAll('div', attrs={'class': 'tv_episode_item'})
                                for tv_episode_item in tv_episode_items:
                                    links = tv_episode_item.findAll('a')
                                    for link in links:
                                        if link.contents[0].strip() == "E%s" % episode:
                                            episode_href = link['href']
                                            try:
                                                episode_href = \
                                                    urlparse.parse_qs(urlparse.urlparse(episode_href).query)['u'][0]
                                            except:
                                                pass
                                            try:
                                                episode_href = \
                                                    urlparse.parse_qs(urlparse.urlparse(episode_href).query)['q'][0]
                                            except:
                                                pass
                                            return self.sources(episode_href)
        except:
            pass
        return []

    def get_key(self):
        url = self.search_link
        html = proxy.get(url, 'searchform')
        parsed_html = BeautifulSoup(html)
        key = parsed_html.findAll('input', attrs={'name': 'key'})[0]["value"]
        return key

    def get_html(self, title, search_link):
        key = self.get_key()
        query = search_link % (urllib.quote_plus(title.replace('\'', '').rsplit(':', 1)[0]), key)
        query = urlparse.urljoin(self.base_link, query)

        html = proxy.get(query, ('index_item'))
        if 'index_item' in html:
            if 'page=2' in html or 'page%3D2' in html:
                html2 = proxy.get(query + '&page=2', 'index_item')
                html += html2
            return html

    def sources(self, url):
        sources = []
        try:
            if url == None: return sources

            url = urlparse.urljoin(self.base_link, url)
            html = proxy.get(url, 'choose_tabs')
            parsed_html = BeautifulSoup(html)

            table_bodies = parsed_html.findAll('tbody')
            for table_body in table_bodies:
                link = table_body.findAll('a')[0]["href"]
                try:
                    link = urlparse.parse_qs(urlparse.urlparse(link).query)['u'][
                        0]  # replace link with ?u= part if present
                except:
                    pass
                try:
                    link = urlparse.parse_qs(urlparse.urlparse(link).query)['q'][
                        0]  # replace link with ?q= part if present
                except:
                    pass

                link = urlparse.parse_qs(urlparse.urlparse(link).query)['url'][
                    0]  # replace link with ?url= part if present
                link = base64.b64decode(link)  # decode base 64
                link = replaceHTMLCodes(link)
                link = link.encode('utf-8')

                host = re.findall('([\w]+[.][\w]+)$', urlparse.urlparse(link.strip().lower()).netloc)[0]
                host = replaceHTMLCodes(host)
                host = host.encode('utf-8')

                quality = table_body.findAll('span')[0]["class"]
                if quality == 'quality_cam' or quality == 'quality_ts':
                    quality = 'CAM'
                elif quality == 'quality_dvd':
                    quality = 'SD'

                sources.append(
                    {'source': host, 'quality': quality, 'scraper': 'Primewire', 'url': link, 'direct': False})

            return sources
        except:
            return sources
