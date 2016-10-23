import base64
import time

import requests


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
        return 'retweeted_status' in tweet or tweet['text'].startswith('RT ')

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
