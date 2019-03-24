# -*- coding: utf-8 -*-
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.statusmessages.interfaces import IStatusMessage
from plone import api
from thokas.id4me.utilities.authentication import get_authentication_utility
from zExceptions import BadRequest, Forbidden
from zope.security import checkPermission
from thokas.id4me import _
from plone.protect.interfaces import IDisableCSRFProtection
from zope.interface import alsoProvides


class ID4meValidateView(BrowserView):

    def __init__(self, context, request):
        alsoProvides(request, IDisableCSRFProtection)
        super(ID4meValidateView, self).__init__(context, request)

    @property
    def auth_util(self):
        return get_authentication_utility()

    def __call__(self):
        state = self.request.form.get('state')
        messages = IStatusMessage(self.request)
        translator = self.context.translate
        navigation_root = api.portal.get_navigation_root(context=self.context)
        if 'error' in self.request.form:
            messages = IStatusMessage(self.request)
            reason = self.request.form.get('error')

            # noinspection PyArgumentList
            messages.add(
                translator(
                    _(u'message_%s_failed' % state),
                    mapping={"reason": reason}
                ),
                type='error'
            )

            self.request.response.redirect(
                navigation_root.absolute_url() + '/@@id4me'
            )
            return

        if 'code' not in self.request.form:
            raise BadRequest('no code given')

        code = self.request.form.get('code')

        if state == 'login':
            user = self.auth_util.verify_user_login(code)
            if user:
                acl_users = getToolByName(self.context, 'acl_users')

                # noinspection PyProtectedMember
                acl_users.session._setupSession(
                    user.getId(),
                    self.request.response
                )

                # noinspection PyArgumentList
                messages.add(
                    translator(_(u'message_login_successful')),
                    type='error'
                )

                self.request.response.redirect(
                    navigation_root.absolute_url()
                )
            else:
                # noinspection PyArgumentList
                messages.add(
                    translator(_(u'message_no_user_connected')),
                    type='error'
                )

                self.request.response.redirect(
                    navigation_root.absolute_url() + '/@@id4me'
                )
        elif state == 'register':
            if not api.portal.get_registry_record(name='plone.enable_self_reg'):
                raise Forbidden()

            user = self.auth_util.register_user(code)
            acl_users = getToolByName(self.context, 'acl_users')

            # noinspection PyProtectedMember
            acl_users.session._setupSession(
                user.getId(),
                self.request.response
            )

            # noinspection PyArgumentList
            messages.add(
                translator(
                    _(u'message_account_created'),
                    mapping={'user_id': user.getId()}
                ),
                type='error'
            )

            self.request.response.redirect(navigation_root.absolute_url())
        elif state == 'connect':
            if api.user.is_anonymous():
                raise Forbidden('No user logged in')
            # if checkPermission('cmf.SetOwnPassword', self.context):
            #    raise Forbidden('No permission to set own password')
            user = api.user.get_current()

            self.auth_util.connect_user_login(user=user, code=code)

            # noinspection PyArgumentList
            messages.add(
                translator(
                    _(u'message_login_connected'),
                    # ToDo: get Identity Agent information
                    mapping={'agent': 'NOT_FOUND'}
                ),
                type='info'
            )

            self.request.response.redirect(navigation_root.absolute_url())
        else:
            # ToDo: handle Case
            raise BadRequest('no state given')
