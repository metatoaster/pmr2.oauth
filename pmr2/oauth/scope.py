import re

from persistent import Persistent

from zope.app.container.contained import Contained
from zope.annotation.interfaces import IAttributeAnnotatable
import zope.interface
from zope.schema import fieldproperty

from Acquisition import aq_parent, aq_inner
from Products.CMFCore.utils import getToolByName

from pmr2.oauth.interfaces import IScopeManager
from pmr2.oauth.interfaces import IDefaultScopeManager
from pmr2.oauth.factory import factory


class ScopeManager(Persistent, Contained):
    """\
    Base scope manager.

    The base scope manager, does nothing on its own, serve as a 
    boilerplate for other scope manager.
    """

    zope.component.adapts(IAttributeAnnotatable, zope.interface.Interface)
    zope.interface.implements(IScopeManager)
    
    def __init__(self):
        pass

    def validate(self, client_key, access_key, **kw):
        """
        See IScopeManager.validate
        """

        raise NotImplemented


class DefaultScopeManager(ScopeManager):
    """\
    Default scope manager.

    The default scope manage only checks whether the name listed in the
    token matches the ones that are allowed, which are stored as a list
    in this manager.
    """

    zope.interface.implements(IDefaultScopeManager)
    default_scopes = fieldproperty.FieldProperty(
        IDefaultScopeManager['default_scopes'])

    def getContainerType(self, container):
        # use getSite() instead of container?
        pt_tool = getToolByName(container, 'portal_types', None)
        if pt_tool is None:
            return

        context = aq_inner(container)
        typeinfo = None

        while context is not None:
            typeinfo = pt_tool.getTypeInfo(context)
            if typeinfo:
                return typeinfo.id
            context = aq_parent(context)

        return

    def validate(self, client_key, access_key, container, name, **kw):
        """
        Default validation.

        Ignore where the value was originally accessed from and focus
        on the container.  Traverse back up the container until we reach
        a registered type, using the names to build our subpath, then
        see if it is in the list of permitted scope for the container
        type.
        """

        if not self.default_scopes:
            return False

        container_type = self.getContainerType(container)
        valid_scopes = self.default_scopes.get(container_type, {})
        if not valid_scopes:
            return False

        # XXX name is not corrected.  Implement unit tests for this 
        # class
        return name in valid_scopes

DefaultScopeManagerFactory = factory(DefaultScopeManager)
