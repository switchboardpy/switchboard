"""
switchboard.conditions
~~~~~~~~~~~~~~~~~

:copyright: (c) 2015 Kyle Adams.
:license: Apache License 2.0, see LICENSE for more details.
"""

# Credit to Haystack for abstraction concepts

import datetime
import re

from .models import EXCLUDE


class Invalid(Exception):  # pragma: nocover
    pass


def titlize(s):
    return s.title().replace('_', ' ')


class Field:
    '''
    Field represents a user input on a parent :class:`ConditionSet`. The user
    provides a value in the Field; that value is the "expected" value. Some
    aspect of the request (as determined by the parent :class:`ConditionSet`)
    provides the "actual" value. If the value and the aspect satisfy the
    Field's specific comparison, then the Field is active.

    For example: suppose we had a ConditionSet setup to look at the requests'
    HTTP_REFERER environment variable. That ConditionSet would have a "referer"
    Field. The value is that Field would be compared against the actual value
    of HTTP_REFERER; if they were equal, the Field would be active.

    Field is primarily a base class, intended to be extended by more specific
    input types.
    '''
    default_help_text = None

    def __init__(self, label=None, help_text=None):
        self.label = label
        self.help_text = help_text or self.default_help_text
        self.set_values(None)

    def set_values(self, name):
        self.name = name
        if name and not self.label:
            self.label = titlize(name)

    def is_active(self, value, actual_value):
        return value == actual_value

    def validate(self, data):
        value = data.get(self.name)
        if value:
            value = self.clean(value)
            is_string = isinstance(value, str)
            assert is_string, 'clean methods must return strings'
        return value

    def clean(self, value):  # pragma: nocover
        return value

    def render(self, value):
        return ('<input type="text" value="%s" name="%s"/>'
                % (value or '', self.name))

    def display(self, value):  # pragma: nocover
        return value


class Boolean(Field):
    '''
    Implements a boolean Field. The actual value being checked is a true or
    false value.
    '''
    def is_active(self, value, actual_value):
        return bool(actual_value)

    def render(self, value):
        return '<input type="hidden" value="1" name="%s"/>' % self.name

    def display(self, value):  # pragma: nocover
        return self.label


class Choice(Field):
    '''
    Implements a select field, where the actual value must match one of the
    options.
    '''
    def __init__(self, choices, **kwargs):
        self.choices = choices
        super().__init__(**kwargs)

    def is_active(self, value, actual_value):
        return actual_value in self.choices and actual_value == value

    def clean(self, value):
        if value not in self.choices:
            raise Invalid
        return value


class Range(Field):
    '''
    Implements a range field, where the actual value must fall between min and
    max values.
    '''
    def is_active(self, value, actual_value):
        return actual_value >= value[0] and actual_value <= value[1]

    def validate(self, data):
        min_limit = data.get(self.name + '[min]')
        max_limit = data.get(self.name + '[max]')
        value = [_f for _f in [min_limit, max_limit] if _f] or None
        return self.clean(value)

    def clean(self, value):
        if value:
            try:
                list(map(int, value))
            except (TypeError, ValueError):
                raise Invalid('You must enter valid integer values.')
        else:
            raise Invalid('You must specify a non-empty range.')
        return '-'.join(value)

    def render(self, value):
        if not value:
            value = ['', '']
        html = (
            '<input type="text" value="%s" placeholder="from" name="%s[min]"/>'
            + ' - '
            + '<input type="text" placeholder="to" value="%s" name="%s[max]"/>'
        )
        return (html % (value[0], self.name, value[1], self.name))

    def display(self, value):
        value = value.split('-')
        return f'{self.label}: {value[0]}-{value[1]}'


class Percent(Range):
    '''
    Implements a percentage field, which is special case of a :class:`Range`.
    In this case, the actual value is modded against 100. If it falls within
    the specified percentile range, then it is active.
    '''
    default_help_text = 'Enter two ranges, e.g. 0-50 is lower 50%.'

    def is_active(self, value, actual_value):
        value = list(map(int, value.split('-')))
        mod = actual_value % 100
        return super().is_active(value, mod)

    def display(self, value):
        value = value.split('-')
        min_value = value[0]
        max_value = value[1]
        diff = int(max_value) - int(min_value)
        return f'{self.label}: {diff}% ({min_value}-{max_value})'

    def clean(self, value):
        value = super().clean(value)
        if value:
            numeric = value.split('-')
            if int(numeric[0]) < 0 or int(numeric[1]) > 100:
                raise Invalid('You must enter values between 0 and 100.')
            if int(numeric[0]) > int(numeric[1]):
                raise Invalid('Start value must be less than end value.')
        return value


class String(Field):  # pragma: nocover
    '''
    Implements a plain string field. Essentially an alias for :class:`Field`,
    since it does a normal string comparison by default.
    '''
    pass


class Regex(String):
    '''
    Implements a regular expression field; the user-provided value is the
    regular expression used to look for matches in the actual value. Much more
    flexible than the :class:`String` field's equality comparison.
    '''
    regex_cache = {}

    def is_active(self, value, actual_value):
        try:
            regex = self.regex_cache[value]
        except KeyError:
            regex = self.regex_cache[value] = re.compile(value)
        return bool(regex.search(actual_value))

    def render(self, value):
        html = ('/<input type="text" value="%s" name="%s" '
                + 'placeholder="regular expression"/>/')
        return html % (value or '', self.name)


class AbstractDate(Field):
    '''
    Implements a date field, but without specifying how the comparison happens,
    e.g., should the actual date fall before or after the specified date? The
    comparison is left to concrete classes for implementation.
    '''
    DATE_FORMAT = "%Y-%m-%d"
    PRETTY_DATE_FORMAT = "%d %b %Y"

    def str_to_date(self, value):
        return datetime.datetime.strptime(value, self.DATE_FORMAT).date()

    def display(self, value):
        date = self.str_to_date(value)
        return f"{self.label}: {date.strftime(self.PRETTY_DATE_FORMAT)}"

    def clean(self, value):
        try:
            date = self.str_to_date(value)
        except ValueError as e:
            msg = ("Date must be a valid date in the format YYYY-MM-DD.\n(%s)"
                   % e.args[0])
            raise Invalid(msg)

        return date.strftime(self.DATE_FORMAT)

    def render(self, value=None):
        if not value:
            value = datetime.date.today().strftime(self.DATE_FORMAT)

        return f'<input type="text" value="{value}" name="{self.name}"/>'

    def is_active(self, value, actual_value):
        assert isinstance(actual_value, datetime.date)
        if isinstance(actual_value, datetime.datetime):
            # datetime.datetime cannot be compared to datetime.date with > and
            # < operators.
            actual_value = actual_value.date()

        condition_date = self.str_to_date(value)
        return self.date_is_active(condition_date, actual_value)

    def date_is_active(self, condition_date, value):
        raise NotImplementedError


class BeforeDate(AbstractDate):
    '''
    Concrete implementation of a date field; checks to see if the actual date
    falls before the specified date.
    '''
    def date_is_active(self, before_this_date, value):
        return value < before_this_date


class OnOrAfterDate(AbstractDate):
    '''
    Concrete implementation of a date field; checks to see if the actual date
    falls on or after the specified date.
    '''
    def date_is_active(self, after_this_date, value):
        return value >= after_this_date


class ConditionSetBase(type):
    def __new__(cls, name, bases, attrs):
        attrs['fields'] = {}

        # Inherit any fields from parent(s).
        parents = [b for b in bases if isinstance(b, ConditionSetBase)]

        for p in parents:
            fields = getattr(p, 'fields', None)

            if fields:
                attrs['fields'].update(fields)

        for field_name, obj in list(attrs.items()):
            if isinstance(obj, Field):
                field = attrs.pop(field_name)
                field.set_values(field_name)
                attrs['fields'][field_name] = field

        return super().__new__(cls, name, bases, attrs)


class ConditionSet(metaclass=ConditionSetBase):
    def __repr__(self):  # pragma: nocover
        return f'<{self.__class__.__name__}>'

    def get_id(self):  # pragma: nocover
        """
        Returns a string representing a unique identifier for this ConditionSet
        instance.
        """
        return f'{self.__module__}.{self.__class__.__name__}'

    def can_execute(self, instance):  # pragma: nocover
        """
        Given an instance, returns a boolean of whether this ConditionSet
        can return a valid condition check.
        """
        return True

    def get_namespace(self):  # pragma: nocover
        """
        Returns a string specifying a unique registration namespace for this
        ConditionSet instance.
        """
        return self.__class__.__name__

    def get_field_value(self, instance, field_name):
        """
        Given an instance, and the name of an attribute, returns the value
        of that attribute on the instance.

        Default behavior will map the ``percent`` attribute to ``id``.
        """
        # XXX: can we come up w/ a better API?
        # Ensure we map ``percent`` to the ``id`` column
        if field_name == 'percent':
            field_name = 'id'
        value = getattr(instance, field_name)
        if callable(value):
            value = value()
        return value

    def has_active_condition(self, condition, instances):
        """
        Given a list of instances, and the condition active for
        this switch, returns a boolean representing if the
        conditional is met, including a non-instance default.
        """
        return_value = None
        for instance in instances + [None]:
            if not self.can_execute(instance):
                continue
            result = self.is_active(instance, condition)
            if result is False:
                return False
            elif result is True:
                return_value = True
        return return_value

    def is_active(self, instance, condition):
        """
        Given an instance, and the condition active for this switch, returns
        a boolean representing if the feature is active.
        """
        return_value = None
        for name, field_conditions in condition.items():
            field = self.fields.get(name)
            if field:
                value = self.get_field_value(instance, name)
                for status, field_cond in field_conditions:
                    if field.is_active(field_cond, value):
                        exclude = status == EXCLUDE
                        if exclude:
                            return False
                        return_value = True
        return return_value

    def get_group_label(self):  # pragma: nocover
        """
        Returns a string representing a human readable version
        of this ConditionSet instance.
        """
        return self.__class__.__name__.title()


class ModelConditionSet(ConditionSet):
    percent = Percent()

    def __init__(self, model):
        self.model = model

    def __repr__(self):  # pragma: nocover
        return f'<{self.__class__.__name__}: {self.model.__name__}>'

    def can_execute(self, instance):
        return isinstance(instance, self.model)

    def get_id(self):
        return f'{self.__module__}.{self.__class__.__name__}({self.get_namespace()})'

    def get_namespace(self):
        raise NotImplementedError('Subclasses should implement this, returning a unique identifier. '
                                  '(e.g. self.model.__tablename__ for SQLAlchemy models)')

    def get_group_label(self):
        return self.get_namespace().title()


class RequestConditionSet(ConditionSet):
    def get_namespace(self):  # pragma: nocover
        return 'request'

    def can_execute(self, instance):
        # There is no Request interface shared across libraries (Webob,
        # Werkzeug) so instead we check for enough attributes to be
        # reasonably certain this is a Request-ish object.
        return (hasattr(instance, 'environ') and
                hasattr(instance, 'headers') and
                hasattr(instance, 'method'))
