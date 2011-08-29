import time
import unittest

import zope.component

import oauth2 as oauth

from pmr2.oauth.consumer import ConsumerManager
from pmr2.oauth.consumer import Consumer

from pmr2.oauth.token import TokenManager
from pmr2.oauth.token import Token

from pmr2.oauth.utility import OAuthUtility

from pmr2.oauth import request

from pmr2.oauth.interfaces import *

from pmr2.oauth.tests.base import TestRequest


class TestRequestAdapter(unittest.TestCase):

    def test_000_request(self):

        params = {
            'oauth_version': "1.0",
            'oauth_nonce': "4572616e48616d6d65724c61686176",
            'oauth_timestamp': "137131200",
            'oauth_consumer_key': "0685bd9184jfhq22",
            'oauth_signature_method': "HMAC-SHA1",
            'oauth_token': "ad180jjd733klru7",
            'oauth_signature': "wOJIO9A2W5mFwDgiDvZbTSMK%2FPY%3D",
        }

        req = TestRequest(oauth_keys=params)
        # Make sure our test request provide the oauth headers...
        self.assert_(req._auth.startswith('OAuth'))
        req = request.BrowserRequestAdapter(req)
        self.assert_(isinstance(req, oauth.Request))
        self.assertEqual(req, params)

    def test_001_request_form(self):
        params = {
            'oauth_version': "1.0",
            'oauth_nonce': "4572616e48616d6d65724c61686176",
            'oauth_timestamp': str(int(time.time())),
        }
        form = {
            'bar': 'blerg',
            'multi': ['FOO','BAR'],
        }
        consumer = oauth.Consumer('consumer-key', 'consumer-secret')
        token = oauth.Token('token-key', 'token-secret')
        req = TestRequest(form=form, oauth_keys=params)
        req = request.BrowserRequestAdapter(req)
        answer = {}
        answer.update(params)
        answer.update(form)
        self.assertEqual(req, answer)

    def test_002_request_basic_auth(self):
        form = {
            'bar': 'blerg',
            'multi': ['FOO','BAR'],
        }
        consumer = oauth.Consumer('consumer-key', 'consumer-secret')
        token = oauth.Token('token-key', 'token-secret')
        req = TestRequest(form=form)
        req._auth = 'Basic ' + 'test:test'.encode('base64')
        req = request.BrowserRequestAdapter(req)
        answer = {}
        answer.update(form)
        self.assertEqual(req, answer)

    def test_003_request_noauth(self):
        form = {
            'bar': 'blerg',
            'multi': ['FOO','BAR'],
        }
        consumer = oauth.Consumer('consumer-key', 'consumer-secret')
        token = oauth.Token('token-key', 'token-secret')
        req = TestRequest(form=form)
        req = request.BrowserRequestAdapter(req)
        answer = {}
        answer.update(form)
        self.assertEqual(req, answer)

    def test_010_request_noform(self):
        form = {}
        consumer = oauth.Consumer('consumer-key', 'consumer-secret')
        token = oauth.Token('token-key', 'token-secret')
        req = TestRequest(form=form)
        req = request.BrowserRequestAdapter(req)
        answer = {}
        answer.update(form)
        self.assertEqual(req, answer)


class TestUtility(unittest.TestCase):

    def test_000_Utility(self):
        params = {
            'oauth_version': "1.0",
            'oauth_nonce': "4572616e48616d6d65724c61686176",
            'oauth_timestamp': int(time.time()),
            'oauth_consumer_key': "consumer-key",
            'oauth_token': "token-key",
        }
        form = {
            'bar': 'blerg',
            'multi': ['FOO','BAR'],
        }

        consumer = oauth.Consumer(params['oauth_consumer_key'],
            'consumer-secret')
        token = oauth.Token(params['oauth_token'], 'token-secret')

        req = TestRequest(oauth_keys=params)
        req = request.BrowserRequestAdapter(req)
        utility = OAuthUtility()
        # just testing so we are not signing anything...
        self.assertRaises(oauth.MissingSignature,
            utility.verify_request, req, consumer, token)


class TestConsumer(unittest.TestCase):

    def setUp(self):
        pass

    def test_000_consumer(self):
        c = Consumer('consumer-key', 'consumer-secret')
        self.assertEqual(c.key, 'consumer-key')
        self.assertEqual(c.secret, 'consumer-secret')

    def test_100_consumer_manager_empty(self):
        m = ConsumerManager()
        self.assertEqual(m.get('consumer-key'), None)

    def test_101_consumer_manager_addget(self):
        m = ConsumerManager()
        c = Consumer('consumer-key', 'consumer-secret')
        m.add(c)
        result = m.get('consumer-key')
        self.assertEqual(result, c)

    def test_102_consumer_manager_doubleadd(self):
        m = ConsumerManager()
        c = Consumer('consumer-key', 'consumer-secret')
        m.add(c)
        self.assertRaises(ValueError, m.add, c)

    def test_102_consumer_manager_remove(self):
        m = ConsumerManager()
        c1 = Consumer('consumer-key', 'consumer-secret')
        c2 = Consumer('consumer-key2', 'consumer-secret')
        m.add(c1)
        m.add(c2)
        m.remove(c1.key)
        m.remove(c2)
        self.assertEqual(len(m._consumers), 0)

    def test_103_consumer_manager_check(self):
        m = ConsumerManager()
        c1 = Consumer('consumer-key', 'consumer-secret')
        c2 = Consumer('consumer-key2', 'consumer-secret')
        m.add(c1)
        self.assertEqual(m.check(c1), True)
        self.assertEqual(m.check('consumer-key'), True)
        self.assertEqual(m.check(c2), False)
        self.assertEqual(m.check('consumer-key2'), False)


class TestToken(unittest.TestCase):

    def setUp(self):
        pass
        #self.manager = ConsumerManager()

    def test_000_token(self):
        token = Token('token-key', 'token-secret')
        self.assertEqual(token.key, 'token-key')
        self.assertEqual(token.secret, 'token-secret')

    def test_010_token_set_verifier(self):
        token = Token('token-key', 'token-secret')
        token.set_verifier()
        verifier = token.verifier
        token.set_verifier()
        self.assertEqual(verifier, token.verifier)
        token.set_verifier(True)
        self.assertNotEqual(verifier, token.verifier)

    def test_020_token_get_callback_url(self):
        token = Token('token-key', 'token-secret')
        token.set_callback(u'http://example.com/')
        token.set_verifier('foo')
        url = token.get_callback_url()
        a = 'http://example.com/?oauth_verifier=foo&oauth_token=token-key'
        self.assertEqual(url, a)

    def test_021_token_get_callback_url(self):
        token = Token('token-key', 'token-secret')
        token.set_callback(u'http://example.com/;bar;?bus=4')
        token.set_verifier('foo')
        url = token.get_callback_url()
        a = 'http://example.com/;bar;?bus=4&oauth_verifier=foo&' \
            'oauth_token=token-key'
        self.assertEqual(url, a)

    def test_011_token_set_verifier(self):
        token = Token('token-key', 'token-secret')
        token.set_verifier('verify')
        self.assertEqual('verify', token.verifier)
        token.set_verifier()
        self.assertEqual('verify', token.verifier)

    def test_100_token_manager_empty(self):
        m = TokenManager()
        self.assertEqual(m.get('token-key'), None)

    def test_101_token_manager_addget(self):
        m = TokenManager()
        c = Token('token-key', 'token-secret')
        m.add(c)
        result = m.get('token-key')
        self.assertEqual(result, c)

    def test_102_token_manager_doubleadd(self):
        m = TokenManager()
        c = Token('token-key', 'token-secret')
        m.add(c)
        self.assertRaises(ValueError, m.add, c)

    def test_102_token_manager_remove(self):
        m = TokenManager()
        t1 = Token('token-key', 'token-secret')
        t2 = Token('token-key2', 'token-secret')
        m.add(t1)
        m.add(t2)
        m.remove(t1.key)
        m.remove(t2)
        self.assertEqual(len(m._tokens), 0)

    def test_200_token_manager_generate_request_token(self):
        m = TokenManager()
        c = Consumer('consumer-key', 'consumer-secret')
        r = oauth.Request.from_consumer_and_token(c, None)
        r['oauth_callback'] = u'oob'
        token = m.generateRequestToken(c, r)
        self.assertEqual(len(m._tokens), 1)
        self.assertEqual(m.get(token.key), token)
        self.assertEqual(m.get(token.key).consumer_key, c.key)

    def test_201_token_manager_generate_request_token_no_callback(self):
        m = TokenManager()
        c = Consumer('consumer-key', 'consumer-secret')
        r = oauth.Request.from_consumer_and_token(c, None)
        self.assertRaises(CallbackValueError, m.generateRequestToken, c, r)

    def test_300_token_manager_generate_access_token(self):
        m = TokenManager()
        c = Consumer('consumer-key', 'consumer-secret')
        r = oauth.Request.from_consumer_and_token(c, None)
        r['oauth_callback'] = u'oob'
        server_token = m.generateRequestToken(c, r)

        # simulate passing only the key and secret to consumer
        request_token = Token(server_token.key, server_token.secret)
        r = oauth.Request.from_consumer_and_token(c, request_token)
        r['oauth_verifier'] = server_token.verifier
        token = m.generateAccessToken(c, r)
        self.assertEqual(len(m._tokens), 1)
        self.assertEqual(m.get(token.key), token)
        self.assertEqual(m.get(token.key).consumer_key, c.key)

    def test_301_token_manager_generate_access_token_no_request_token(self):
        m = TokenManager()
        c = Consumer('consumer-key', 'consumer-secret')
        r = oauth.Request.from_consumer_and_token(c, None)
        self.assertRaises(TokenInvalidError, m.generateAccessToken, c, r)

    def test_302_token_manager_generate_access_token_no_verifier(self):
        m = TokenManager()
        c = Consumer('consumer-key', 'consumer-secret')
        r = oauth.Request.from_consumer_and_token(c, None)
        r['oauth_callback'] = u'oob'
        server_token = m.generateRequestToken(c, r)

        # simulate passing only the key and secret to consumer
        request_token = Token(server_token.key, server_token.secret)
        r = oauth.Request.from_consumer_and_token(c, request_token)
        self.assertRaises(TokenInvalidError, m.generateAccessToken, c, r)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestRequestAdapter))
    suite.addTest(makeSuite(TestUtility))
    suite.addTest(makeSuite(TestConsumer))
    suite.addTest(makeSuite(TestToken))
    return suite