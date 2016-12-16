"""
Functional tests
~~~~~~~~~~~~~~~~

A functional test suite for running through the key actions in the admin UI.
Note that the best way to run this is by running ``make functional-test`` from
the project's root directory. If run directly (e.g., via ``nosetests
example``, the example app should already be running in another console.

.. note::Firefox Required
    By default the functional tests run in Firefox, which means it needs
    to be installed before attempting to run.

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

import os
import shutil

from nose.tools import assert_true, assert_false
from splinter import Browser

from switchboard import configure
from switchboard.models import (
    DISABLED,
    SELECTIVE,
    GLOBAL,
    Switch,
)

configure()

url = 'http://localhost:8080/'
admin_url = url + '_switchboard/'


def assert_switch_active(browser, url=url):
    browser.visit(url)
    assert_true(browser.is_text_present('is active'),
                'Switch is not active')


def assert_switch_inactive(browser, url=url):
    browser.visit(url)
    assert_true(browser.is_text_present('is NOT active'),
                'Switch is not inactive')


def drop_datastore():
    Switch.drop()


class TestAdmin(object):
    @classmethod
    def setup_class(cls):
        cls.b = Browser()
        # Ensure we're working with a clean slate.
        drop_datastore()

    @classmethod
    def teardown_class(cls):
        cls.b.quit()

    def setup(self):
        # Make sure the example switch is activated by at least
        # one visit.
        self.b.visit(url)

    def teardown(self):
        drop_datastore()

    def test_root(self):
        assert_switch_inactive(self.b)

    def test_admin_index(self):
        self.b.visit(admin_url)
        assert_true(len(self.b.find_by_id('id_example')))

    def test_change_status(self):
        # Set the switch to global status and verify it's active.
        self.b.visit(admin_url)
        self.b.select('status_example', GLOBAL)
        alert = self.b.get_alert()
        alert.accept()
        css = '#id_example[data-switch-status="{status}"]'
        active_selector = css.format(status=GLOBAL)
        is_status_updated = self.b.is_element_present_by_css(active_selector,
                                                             wait_time=10)
        assert_true(is_status_updated, 'Switch status not updated')
        self.b.visit(url)
        assert_switch_active(self.b)
        # Set the switch back to inactive and verify.
        self.b.visit(admin_url)
        self.b.select('status_example', DISABLED)
        inactive_selector = css.format(status=DISABLED)
        is_status_updated = self.b.is_element_present_by_css(inactive_selector,
                                                             wait_time=10)
        assert_true(is_status_updated, 'Switch status not updated')
        self.b.visit(url)
        assert_switch_inactive(self.b)

    def test_add_and_delete_condition(self):
        self.b.visit(admin_url)
        # Click the button.
        switch = self.b.find_by_id('id_example').first
        btn = switch.find_by_css('a[href="#add-condition"]')
        btn.click()
        # Setup a condition.
        form = switch.find_by_css('.conditions-form').first
        assert_true(form.visible, 'Add conditions form is not visible.')
        condition_id = 'switchboard.builtins.QueryStringConditionSet,regex'
        # Can't use select() here because it doesn't support <optgroup>.
        css = 'select[name="{}"] option[value="{}"]'.format(
            'condition',
            condition_id,
        )
        form.find_by_css(css)._element.click()
        css = '.fields[data-path="{}"]'.format(condition_id.replace(',', '.'))
        field = form.find_by_css(css)
        assert_true(field.visible, 'Condition field is not visible')
        data_value = 'test'
        field.find_by_name('regex').fill(data_value)
        field.find_by_css('button[type="submit"]').first.click()
        # Verify the condition has been created.
        data_switch, data_field = condition_id.split(',')
        condition_css = (
            '#id_example ' +
            '[data-switch="{}"][data-field="{}"][data-value="{}"]'
        )
        condition_css = condition_css.format(
            data_switch,
            data_field,
            data_value,
        )
        is_created = self.b.is_element_present_by_css(condition_css,
                                                      wait_time=10)
        assert_true(is_created, 'Condition was not created')
        # Set the proper status.
        self.b.select('status_example', SELECTIVE)
        # Ensure that the switch is off when condition is not met...
        assert_switch_inactive(self.b, url=url + '?foo')
        # ...and on when the condition is met.
        assert_switch_active(self.b, url=url + '?' + data_value)
        # Delete the condition.
        self.b.visit(admin_url)
        cond = self.b.find_by_css(condition_css).first
        cond.find_by_css('a[href="#delete-condition"]').first.click()
        is_deleted = self.b.is_element_not_present_by_css(condition_css,
                                                          wait_time=10)
        assert_true(is_deleted, 'Condition was not deleted')
        # Verify that the switch is no longer active.
        assert_switch_inactive(self.b, url=url + '?test')

    def test_add_edit_delete_switch(self):
        self.b.visit(admin_url)
        # Add the switch.
        self.b.find_link_by_href('#add-switch').first.click()
        drawer = self.b.find_by_css('.drawer').first
        assert_true(drawer.visible, 'Drawer is not visible')
        key = 'test1'
        drawer.find_by_css('input[name="key"]').first.fill(key)
        drawer.find_by_css('a.submit-switch').first.click()
        # Verify the addition.
        is_added = self.b.is_element_present_by_css('#id_{}'.format(key),
                                                    wait_time=10)
        assert_true(is_added, 'Switch was not added.')
        assert_false(drawer.visible, 'Drawer is not hidden')
        # Edit the switch.
        self.show_switch_actions()
        css = '#id_{} a[href="#edit-switch"]'.format(key)
        self.b.find_by_css(css).first.click()
        assert_true(drawer.visible, 'Drawer is not visible')
        label = 'Foobar'
        drawer.find_by_css('input[name="label"]').first.fill(label)
        drawer.find_by_css('a.submit-switch').first.click()
        # Verify the edit.
        is_edited = self.b.is_text_present(label, wait_time=10)
        assert_true(is_edited, 'Switch was not edited.')
        assert_false(drawer.visible, 'Drawer is not hidden')
        # Delete the switch.
        self.show_switch_actions()
        css = '#id_{} a[href="#delete-switch"]'.format(key)
        self.b.find_by_css(css).first.click()
        alert = self.b.get_alert()
        alert.accept()
        # Verify the deletion.
        is_deleted = self.b.is_element_not_present_by_css('#id_{}'.format(key),
                                                          wait_time=10)
        assert_true(is_deleted, 'Switch was not deleted.')

    def show_switch_actions(self):
        '''
        Need to temporarily suspend show-on-hover in order to interact with
        the links (can't click on links that are hidden).
        '''
        js = "$('.switches .actions').css('visibility', 'visible')"
        self.b.execute_script(js)
