# -*- coding: utf-8 -*-
from django.utils.safestring import EscapeUnicode, SafeData


class BoundRow(object):
    """Represents a *specific* row in a table.

    :class:`BoundRow` objects are a container that make it easy to access the
    final 'rendered' values for cells in a row. You can simply iterate over a
    :class:`BoundRow` object and it will take care to return values rendered
    using the correct method (e.g. :meth:`Column.render_FOO`)

    To access the rendered value of each cell in a row, just iterate over it:

    .. code-block:: python

        >>> import django_tables as tables
        >>> class SimpleTable(tables.Table):
        ...     a = tables.Column()
        ...     b = tables.CheckBoxColumn(attrs={'name': 'my_chkbox'})
        ...
        >>> table = SimpleTable([{'a': 1, 'b': 2}])
        >>> row = table.rows[0]  # we only have one row, so let's use it
        >>> for cell in row:
        ...     print cell
        ...
        1
        <input type="checkbox" name="my_chkbox" value="2" />

    Alternatively you can treat it like a list and use indexing to retrieve a
    specific cell. It should be noted that this will raise an IndexError on
    failure.

    .. code-block:: python

        >>> row[0]
        1
        >>> row[1]
        u'<input type="checkbox" name="my_chkbox" value="2" />'
        >>> row[2]
        ...
        IndexError: list index out of range

    Finally you can also treat it like a dictionary and use column names as the
    keys. This will raise KeyError on failure (unlike the above indexing using
    integers).

    .. code-block:: python

        >>> row['a']
        1
        >>> row['b']
        u'<input type="checkbox" name="my_chkbox" value="2" />'
        >>> row['c']
        ...
        KeyError: 'c'

    """
    def __init__(self, table, record):
        """Initialise a new :class:`BoundRow` object where:

        * *table* is the :class:`Table` in which this row exists.
        * *record* is a single record from the data source that is posed to
          populate the row. A record could be a :class:`Model` object, a
          ``dict``, or something else.

        """
        self._table = table
        self._record = record

    @property
    def table(self):
        """The associated :term:`table`."""
        return self._table

    @property
    def record(self):
        """The data record from the data source which is used to populate this
        row with data.

        """
        return self._record

    def __iter__(self):
        """Iterate over the rendered values for cells in the row.

        Under the hood this method just makes a call to :meth:`__getitem__` for
        each cell.

        """
        for column in self.table.columns:
            # this uses __getitem__, using the name (rather than the accessor)
            # is correct – it's what __getitem__ expects.
            yield self[column.name]

    def __getitem__(self, name):
        """Returns the final rendered value for a cell in the row, given the
        name of a column.

        """
        bound_column = self.table.columns[name]
        raw = bound_column.accessor.resolve(self.record)
        kwargs = {
            'value': raw if raw is not None else bound_column.default,
            'record': self.record,
            'column': bound_column.column,
            'bound_column': bound_column,
            'bound_row': self,
            'table': self._table,
        }
        render_FOO = 'render_' + bound_column.name
        render = getattr(self.table, render_FOO, bound_column.column.render)
        try:
            return render(**kwargs)
        except TypeError as e:
            # Let's be helpful and provide a decent error message, since
            # render() underwent backwards incompatible changes.
            if e.message.startswith('render() got an unexpected keyword'):
                if hasattr(self.table, render_FOO):
                    cls = self.table.__class__.__name__
                    meth = render_FOO
                else:
                    cls = kwargs['column'].__class__.__name__
                    meth = 'render'
                msg = 'Did you forget to add **kwargs to %s.%s() ?' % (cls, meth)
                raise TypeError(e.message + '. ' + msg)

    def __contains__(self, item):
        """Check by both row object and column name."""
        if isinstance(item, basestring):
            return item in self.table._columns
        else:
            return item in self


class BoundRows(object):
    """
    Container for spawning :class:`.BoundRow` objects.

    The :attr:`.tables.Table.rows` attribute is a :class:`.BoundRows` object.
    It provides functionality that would not be possible with a simple iterator
    in the table class.

    """
    def __init__(self, table):
        """
        Initialise a :class:`Rows` object. *table* is the :class:`Table` object
        in which the rows exist.

        """
        self.table = table

    def all(self):
        """
        Return an iterable for all :class:`BoundRow` objects in the table.

        """
        for record in self.table.data:
            yield BoundRow(self.table, record)

    def page(self):
        """
        If the table is paginated, return an iterable of :class:`.BoundRow`
        objects that appear on the current page, otherwise :const:`None`.

        """
        if not hasattr(self.table, 'page'):
            return None
        return iter(self.table.page.object_list)

    def __iter__(self):
        """Convience method for :meth:`.BoundRows.all`"""
        return self.all()

    def __len__(self):
        """Returns the number of rows in the table."""
        return len(self.table.data)

    # for compatibility with QuerySetPaginator
    count = __len__

    def __getitem__(self, key):
        """Allows normal list slicing syntax to be used."""
        if isinstance(key, slice):
            result = list()
            for row in self.table.data[key]:
                result.append(BoundRow(self.table, row))
            return result
        elif isinstance(key, int):
            return BoundRow(self.table, self.table.data[key])
        else:
            raise TypeError('Key must be a slice or integer.')