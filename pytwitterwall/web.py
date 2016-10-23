from datetime import datetime

import jinja2
from flask import Flask, render_template, url_for

from .twitter import TwitterWall


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
                raise RuntimeError('Unknown entity')
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
