import json

import aiohttp_jinja2
import jinja2


def setup_jinja2(app):
    """Setup Jinja2 template engine for the web application"""
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader("static/templates"),
        context_processors=[aiohttp_jinja2.request_processor],
        filters={"json": json.dumps},
    )
