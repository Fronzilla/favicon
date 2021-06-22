import os
import requests

from typing import Optional
from aiohttp import web
from favicon import FaviconManager

manager = FaviconManager()


async def get_favicon(link: str):
    """
    :param link:
    :return:
    """
    return await manager.get(link)


async def handle(request):
    """
    :return:
    """
    url: Optional[str] = request.query['url']
    try:
        result = await get_favicon(url)
    except requests.exceptions.ConnectionError:
        return web.json_response({'error': 'nodename nor servname provided, or not known'}, status=500)

    return web.json_response(result, status=200)


async def init():
    app = web.Application()
    app.router.add_get("/", handle)
    return app


if __name__ == "__main__":
    application = init()
    web.run_app(application, port=os.getenv('PORT'))

# проверить размер иконки и если она квардратнеая - больний приортрирет
