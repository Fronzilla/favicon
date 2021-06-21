"""
Менеджер для поиска favicon.ico на web - ресурсе
"""

__author__ = 'av.nikitin'

import os
import re
import requests

from typing import Dict, Optional, Set, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup


SIZE_RE = re.compile(r'(?P<width>\d{2,4})x(?P<height>\d{2,4})', flags=re.IGNORECASE)


@dataclass(frozen=True)
class Icon:
    url: str
    width: int
    height: int
    format: str


class FaviconManager:

    META_NAMES = ['msapplication-TileImage', 'og:image']

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/33.0.1750.152 Safari/537.36'
    }
    LINK_RELS = [
        'icon',
        'shortcut icon',
        'apple-touch-icon',
        'apple-touch-icon-precomposed',
    ]

    @property
    def headers(self):
        return self.HEADERS

    @headers.setter
    def headers(self, value):
        self.HEADERS = value

    def get(self, url: str, biggest: bool = True, **request_kwargs) -> Dict:
        """
        По переданному url получить все favicon
        :param url: Целевая страница.
        :param biggest: Возвращать самое большую favicon или все
        :param request_kwargs: Аргументы заголовков запроса
        :return: Json формата
        """

        request_kwargs.setdefault('headers', self.HEADERS)
        request_kwargs.setdefault('allow_redirects', True)
        request_kwargs.setdefault('verify', False)

        response = requests.get(url, **request_kwargs)
        response.raise_for_status()

        icons = set()

        default_icon = self.default(response.url, **request_kwargs)
        if default_icon:
            icons.add(default_icon)

        link_icons = self.tags(response.url, response.text)
        if link_icons:
            icons.update(link_icons)

        result = sorted(icons, key=lambda i: i.width + i.height, reverse=True)

        if not result:
            return {}

        if biggest:
            result_ = result[0].__dict__

        else:
            result_ = {'favicons': {}}
            for index, item in enumerate(result):
                result_['favicons'].update({index: item.__dict__})

        return result_

    def tags(self, url: str, html: str) -> Set[Icon]:
        """ Получить favicon по ссылке и мета тегам.

        Например
           <link rel="apple-touch-icon" sizes="144x144" href="apple-touch-icon.png">
           <meta name="msapplication-TileImage" content="favicon.png">

        :param url: Целевой url.
        :param html: HTML страница.
        :return:
        """

        soup = BeautifulSoup(html, features='html.parser')
        icons, meta_tags, link_tags = set(), set(), set()

        for rel in self.LINK_RELS:
            for link_tag in soup.find_all(
                    'link', attrs={'rel': lambda r: r and r.lower() == rel, 'href': True}
            ):
                link_tags.add(link_tag)

        for meta_tag in soup.find_all('meta', attrs={'content': True}):
            meta_type = meta_tag.get('name') or meta_tag.get('property') or ''
            meta_type = meta_type.lower()
            for name in self.META_NAMES:
                if meta_type == name.lower():
                    meta_tags.add(meta_tag)

        for tag in link_tags | meta_tags:
            href = tag.get('href', '') or tag.get('content', '')
            href = href.strip()

            if not href or href.startswith('data:image/'):
                continue

            if self.is_absolute(href):
                url_parsed = href
            else:
                url_parsed = urljoin(url, href)

            # '//cdn.network.com/favicon.png' или `icon.png?v2`
            scheme = urlparse(url).scheme
            url_parsed = urlparse(url_parsed, scheme=scheme)

            width, height = self.dimensions(tag)
            _, ext = os.path.splitext(url_parsed.path)

            icon = Icon(url_parsed.geturl(), width, height, ext[1:].lower())
            icons.add(icon)

        return icons

    @staticmethod
    def default(url: str, **request_kwargs: Dict) -> Optional[Icon]:
        """
        Получить default favicon.ico.
        :param url: Целевой Url.
        :param request_kwargs: Аргументы заголовков запроса
        :return: Icon либо None.
        """

        parsed = urlparse(url)

        favicon_url = urlunparse((parsed.scheme, parsed.netloc, 'favicon.ico', '', '', ''))
        response = requests.head(favicon_url, **request_kwargs)

        if response.status_code == 200:
            return Icon(response.url, 0, 0, 'ico')

    @staticmethod
    def is_absolute(url: str) -> bool:
        """
        Проверка того, является ли Url абсолютным
        :param url: Целевой Url
        :return:
        """
        return bool(urlparse(url).netloc)

    @staticmethod
    def dimensions(tag: 'BeautifulSoup.element.Tag') -> Tuple[int, int]:
        """
        Вычисление размера иконки
        :param tag: Link or meta tag.
        :return: Если размер будет найден - Tuple[int, int], в противном случае Tuple[0,0]
        """
        sizes = tag.get('sizes', '')
        if sizes and sizes != 'any':
            size = sizes.split(' ')  # '16x16 32x32 64x64'
            size.sort(reverse=True)
            width, height = re.split(r'[x\xd7]', size[0])
        else:
            filename = tag.get('href') or tag.get('content')
            size = SIZE_RE.search(filename)
            if size:
                width, height = size.group('width'), size.group('height')
            else:
                width, height = '0', '0'

        width = ''.join(c for c in width if c.isdigit())
        height = ''.join(c for c in height if c.isdigit())

        return int(width), int(height)

