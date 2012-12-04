import urllib

import zope.component
import zope.interface
from zope.app.component.hooks import getSite
from zope.publisher.browser import BrowserPage

from zExceptions import BadRequest
from zExceptions import Forbidden
from zExceptions import Unauthorized

from z3c.form import button

from Products.CMFCore.utils import getToolByName

from pmr2.z3cform import form

from pmr2.oauth import MessageFactory as _
from pmr2.oauth.interfaces import *
from pmr2.oauth.browser.template import ViewPageTemplateFile
from pmr2.oauth.browser.template import path


class BaseTokenPage(BrowserPage):

    # token to return
    token = None

    def _checkConsumer(self, key):
        cm = zope.component.getMultiAdapter((self.context, self.request),
            IConsumerManager)

        consumer = cm.getValidated(key)
        if not consumer:
            raise ConsumerInvalidError('invalid consumer')
        return consumer

    def _checkToken(self, key):
        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)

        token = tm.get(key)
        if not token:
            raise TokenInvalidError('invalid token')
        return token

    def _verifyToken(self, oauth):
        # Return the correct OAuth method for the respective token 
        # request page.
        raise NotImplementedError()

    def getOAuth1(self):
        if not hasattr(self.request, '_pmr2_oauth1_'):
            site = getSite()
            oauthAdapter = zope.component.getMultiAdapter((site, self.request),
                IOAuthAdapter)
            try:
                result, oauth1 = self._verifyToken(oauthAdapter)
            except ValueError:
                raise BadRequest()
            if not result:
                raise Forbidden()
            #self.request._pmr2_oauth1_ = oauth1
            return oauth1
        else:
            # Prepared by the run at the plugin.
            return self.request._pmr2_oauth1_

    def update(self):
        raise NotImplementedError()

    def render(self):
        token = self.token
        data = {
            'oauth_token': token.key,
            'oauth_token_secret': token.secret,
        }
        if token.callback is not None:
            data['oauth_callback_confirmed'] = 'true'
        return urllib.urlencode(data)

    def __call__(self):
        self.update()
        return self.render()


class RequestTokenPage(BaseTokenPage):

    def _verifyToken(self, oauth):
        # See parent class
        return oauth.verify_request_token_request()

    def update(self):
        oauth1 = self.getOAuth1()

        # This is an 8-bit protocol, so we cast the oauthlib request
        # parameters into something we would expect from the http spec.
        # If this dies in a fire it is not my problem.
        consumer_key = str(oauth1.client_key)
        callback = str(oauth1.callback_uri)

        # create request token
        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        self.token = tm.generateRequestToken(consumer_key, callback)


class GetAccessTokenPage(BaseTokenPage):

    def _verifyToken(self, oauth):
        # See parent class
        return oauth.verify_access_token_request()

    def update(self):
        oauth1 = self.getOAuth1()

        # This is an 8-bit protocol, so we cast the oauthlib request
        # parameters into something we would expect from the http spec.
        # If this dies in a fire it is not my problem.
        consumer_key = str(oauth1.client_key)
        token_key = str(oauth1.resource_owner_key)
        verifier = str(oauth1.verifier)

        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        self.token = tm.generateAccessToken(consumer_key, token_key)


class AuthorizeTokenForm(form.PostForm, BaseTokenPage):

    ignoreContext = True
    invalidTokenMessage = _(u'Invalid Token.')
    invalidConsumerMessage = _(
        u'Consumer associated with this key is invalid.')
    deniedMessage = _(
        u'Token has been denied.')
    token = None
    consumer = None
    consumer_key = ''
    description = ''
    verifier = ''
    statusTemplate = ViewPageTemplateFile(path('authorize_status.pt'))
    verifierTemplate = ViewPageTemplateFile(path('authorize_verifier.pt'))
    template = ViewPageTemplateFile(path('authorize_question.pt'))
    _errors = False

    def _update(self):
        token_key = self.request.form.get('oauth_token', None)
        token = self._checkToken(token_key)
        consumer = self._checkConsumer(token.consumer_key)
        self.token = token
        self.consumer = consumer
        self.consumer_key = consumer.key

    def update(self):
        """\
        We do need an actual user, not sure which permission level will
        get me to do what I want in the zcml, hence we will need to
        manually check.
        """

        self.request['disable_border'] = True
        mt = getToolByName(self.context, 'portal_membership')
        if mt.isAnonymousUser():
            # should trigger a redirect to some login mechanism.
            raise Unauthorized()

        try:
            self._update()
        except TokenInvalidError, e:
            self._errors = self.invalidTokenMessage
        except ConsumerInvalidError, e:
            self._errors = self.invalidConsumerMessage

        if self._errors:
            self.status = self._errors
            self._errors = True

        return super(AuthorizeTokenForm, self).update() 

    def render(self):
        if self._errors:
            return self.statusTemplate()
        if self.verifier:
            return self.verifierTemplate()
        return super(AuthorizeTokenForm, self).render()

    def scope(self):
        # XXX make this hook into the scope manager such that subclasses
        # can implement more friendly renderings of requested resources
        # in a more friendly way so that these views don't need to be
        # customized.
        return ''

    @button.buttonAndHandler(_('Grant access'), name='approve')
    def handleApprove(self, action):
        """\
        User approves this token.
        
        Redirect user to the callback URL to give the provider the OAuth
        Verifier key.
        """

        if self._errors or not self.token:
            return

        mt = getToolByName(self.context, 'portal_membership')
        user = mt.getAuthenticatedMember().id

        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        tm.claimRequestToken(self.token, user)
        if not self.token.callback == 'oob':
            callback_url = self.token.get_callback_url()
            # XXX here is where the callback URL will fail.
            return self.request.response.redirect(callback_url)
        # handle oob
        self.verifier = self.token.verifier

    @button.buttonAndHandler(_('Deny access'), name='deny')
    def handleDeny(self, action):
        """\
        User denies this token
        """

        token_key = self.request.form.get('oauth_token', None)
        tm = zope.component.getMultiAdapter((self.context, self.request),
            ITokenManager)
        tm.remove(token_key)
        if not self.token.callback == 'oob':
            callback_url = self.token.get_callback_url()
            return self.request.response.redirect(callback_url)
        self.status = self.deniedMessage
        self._errors = True
