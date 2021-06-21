from typing import Optional
from flask import Flask, request
from flask import jsonify

from favicon import FaviconManager

app = Flask(__name__)


def get_favicon(link: str):
    """
    :param link:
    :return:
    """
    return FaviconManager().get(link)


@app.route("/")
def faviconroute():
    url: Optional[str] = request.args.get('url', None)
    result = get_favicon(url)
    return jsonify(result)


if __name__ == '__main__':
    app.run()
