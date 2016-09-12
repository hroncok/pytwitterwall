import base64
import configparser
import time
import sys
from datetime import datetime

import click
import jinja2
import requests
from flask import Flask, render_template, url_for


class TwitterWall:
    """Class for Twitter handling"""

    def __init__(self, api_key, api_secret):
        self.session = self._create_session(api_key, api_secret)
        self.last_seen = 0

    def _create_session(self, api_key, api_secret):
        session = requests.Session()
        secret = '{}:{}'.format(api_key, api_secret)
        secret64 = base64.b64encode(secret.encode('ascii')).decode('ascii')

        headers = {
            'Authorization': 'Basic {}'.format(secret64),
            'Host': 'api.twitter.com',
        }

        r = session.post('https://api.twitter.com/oauth2/token',
                         headers=headers,
                         data={'grant_type': 'client_credentials'})

        bearer_token = r.json()['access_token']

        def bearer_auth(req):
            req.headers['Authorization'] = 'Bearer ' + bearer_token
            return req

        session.auth = bearer_auth
        return session

    def search(self, **kwargs):
        """Searches the given query, returns up to count results"""
        r = self.session.get('https://api.twitter.com/1.1/search/tweets.json',
                             params=kwargs)
        r.raise_for_status()
        return r.json()['statuses']

    def tweets(self, query, count):
        """Performs an initial search, returns the tweets DESC"""
        statuses = self.search(q=query, count=count, result_type='recent')
        if statuses:
            self.last_seen = statuses[0]['id']
        self.query = query
        return statuses

    def more_tweets(self):
        """Gets new tweets since last time"""
        statuses = self.search(q=self.query, since_id=self.last_seen,
                               result_type='recent')
        if statuses:
            self.last_seen = statuses[0]['id']
        return reversed(statuses)

    def infinite_generator(self, query, initial_count, interval):
        """Do an infinite loop and yield the tweets"""
        yield from reversed(self.tweets(query, initial_count))
        while True:
            yield from self.more_tweets()
            time.sleep(interval)

    @classmethod
    def format_tweet(cls, tweet):
        """Return a formated line for prinitng"""
        fmt = {
            'text': tweet['text'],
            'username': tweet['user']['screen_name'],
            'at': tweet['created_at']
        }
        return '{text}\nby @{username} at {at}\n'.format(**fmt)

    @classmethod
    def is_retweet(cls, tweet):
        """Check if the tweet is a retweet"""
        return tweet['retweeted'] or tweet['text'].startswith('RT ')

    @classmethod
    def is_reply(cls, tweet):
        """Check if the tweet is a reply"""
        return (bool(tweet['in_reply_to_user_id']) or
                tweet['text'].startswith('@'))

    def infinite_formater(self, query, initial_count,
                          interval, retweets, replies):
        """Return infinite stream of formated tweets"""
        for tweet in self.infinite_generator(query, initial_count, interval):
            if ((retweets or not self.is_retweet(tweet)) and
                    (replies or not self.is_reply(tweet))):
                yield self.format_tweet(tweet)

    def infinite_printer(self, query, initial_count,
                         interval, retweets, replies):
        """Print tweets as they come in"""
        for tweet in self.infinite_formater(query, initial_count,
                                            interval, retweets, replies):
            print(tweet)


def credentials(path):
    """Read credentials from a given config file"""
    config = configparser.ConfigParser()
    config.read(path)
    return config['twitter']['key'], config['twitter']['secret']


app = Flask(__name__)


@app.template_filter('time')
def convert_time(text):
    """Convert the time format to a different one"""
    dt = datetime.strptime(text, '%a %b %d %H:%M:%S %z %Y')
    return dt.strftime('%c')


def combine(text, starts, append):
    """Combine intermediate tweet representation to one str"""
    strlist = []
    i = 0
    while True:
        oldi = i
        while i not in starts and i < len(text):
            i += 1
        strlist.append(text[oldi:i])
        if not i < len(text):
            break
        strlist.append(starts[i]['html'])
        i = starts[i]['indices'][1]
    strlist.append(append)
    return ''.join(strlist)


def htmlzie(entities, text):
    """Converts a tweet to rich HTML form"""
    starts = {}  # starting indexes will be keys
    append = ''  # what shell go to the end of the tweet
    link = '<a href="{}">{}</a>'
    twitter = 'https://twitter.com/'
    for k, v in entities.items():
        for entity in v:
            s, e = entity['indices']
            snip = text[s:e]
            if k == 'user_mentions':
                name = entity['screen_name']
                html = link.format(twitter + name, snip)
            elif k == 'hashtags':
                hashtag = entity['text']
                url = url_for('wall', hashtag=hashtag.lower())
                html = link.format(url, snip)
            elif k == 'symbols':
                symbol = entity['text']
                url = twitter + 'search?q=%24{}&src=ctag'.format(symbol)
                html = link.format(url, snip)
            elif k in ['media', 'extended_entities', 'urls']:
                html = link.format(entity['url'], entity['display_url'])
                if k != 'urls':
                    append = '<br /><img src="{}:thumb" />'.format(
                        entity['media_url_https'])
            else:
                assert 'Not gonna happen'
            entity['html'] = html
            starts[s] = entity
    return combine(text, starts, append)


@app.template_filter('enrich')
def enrich_tweet(tweet):
    """Add links and media tot he tweet"""
    text = htmlzie(tweet['entities'], tweet['text'])
    return jinja2.Markup(text)


@app.route('/')
@app.route('/<hashtag>/')
def wall(hashtag='python'):
    tw = TwitterWall(app.config['API_KEY'], app.config['API_SECRET'])
    query = '#' + hashtag
    tweets = tw.tweets(query, 25)
    return render_template('wall.html', tweets=tweets, hashtag=query)


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


if __name__ == '__main__':
    cli()
