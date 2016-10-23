import configparser
import sys

import click

from .twitter import TwitterWall


def credentials(path):
    """Read credentials from a given config file"""
    config = configparser.ConfigParser()
    config.read(path)
    return config['twitter']['key'], config['twitter']['secret']


@click.group()
def cli():
    pass


@cli.command()
@click.option('--debug/--no-debug', default=False,
              help='Whether to run in debug mode, defaults is not to.')
@click.option('--config', default='./auth.cfg',
              help='Path for the auth config file')
def web(debug, config):
    """Run the web twitter wall"""
    from .web import app
    app.config['API_KEY'], app.config['API_SECRET'] = credentials(config)
    if debug:
        app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=debug)


@cli.command()
@click.option('--query', default='#python',
              help='The query to search for.')
@click.option('--initial-count', default=15,
              help='Number of tweets to get when starting.')
@click.option('--interval', default=10,
              help='Number of seconds to wait between polls.')
@click.option('--config', default='./auth.cfg',
              help='Path for the auth config file')
@click.option('--retweets/--no-retweets', default=False,
              help='Whether to show retweets, defaults is no.')
@click.option('--replies/--no-replies', default=True,
              help='Whether to show replies, defaults is yes.')
def console(query, initial_count, interval, config, retweets, replies):
    """Run the command line twitter wall"""
    try:
        tw = TwitterWall(*credentials(config))
        tw.infinite_printer(query, initial_count, interval, retweets, replies)
    except BaseException as e:
        print(e, file=sys.stderr)
