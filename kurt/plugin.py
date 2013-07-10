# Copyright (C) 2012 Tim Radvan
#
# This file is part of Kurt.
#
# Kurt is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# Kurt is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with Kurt. If not, see <http://www.gnu.org/licenses/>.

"""
To add support for a new file format, write a new :class:`KurtPlugin` subclass::

    import kurt
    from kurt.plugin import Kurt, KurtPlugin

    class MyScratchModPlugin(KurtPlugin):
        def load(self, path):
            f = open(path)
            kurt_project = kurt.Project()
            # ... set kurt_project attributes ... #
            return kurt_project

        def save(self, path, kurt_project):
            f = open(path, "w")
            # ... save kurt_project attributes to file ...

    Kurt.register(MyScratchModPlugin())

Take a look at :mod:`kurt.scratch20` for a more detailed example.


List available plugins
~~~~~~~~~~~~~~~~~~~~~~

To get a list of the plugins registered with :class:`Kurt`:

    >>> kurt.plugin.Kurt.plugins
    {'scratch14': kurt.scratch14.Scratch14Plugin()}

You should see your plugin in the output, unless you forgot to :attr:`register
<Kurt.register>` it.


Notes
~~~~~

Some things to keep in mind:

* Most Scratch file formats have the *stage* as the base object -- so project
  attributes, such as the notes and the list of sprites, are stored on the
  stage object.

"""

from collections import OrderedDict

import kurt



class KurtPlugin(object):
    """Handles a specific file format.

    Loading and saving converts between a :class:`Project`, kurt's internal
    representation, and a file of this format.

    """

    name = "scratch14"
    """Short name of this file format, Python identifier style. Used internally
    by kurt.

    Examples: ``"scratch14"``, ``"scratch20.sprite"``, ``"byob3"``, ``"snap"``

    """

    display_name = "Scratch 2.0 Sprite"
    """Human-readable name of this file format. May be displayed to the user.
    Should not contain "Project" or "File".

    Examples: ``"Scratch 1.4"``, ``"Scratch 2.0 Sprite"``, ``"BYOB 3.1"``

    """

    extension = ".sb"
    """The extension used by this format, with leading dot.

    Used by :attr:`Project.load` to recognise its files.

    """

    features = []
    """A list of the :class:`Features <Feature>` that the plugin supports."""

    blocks = []
    """The list of :class:`TranslatedBlockType` objects supported by this
    plugin, in the order they appear in the program's interface.

    """

    def __repr__(self):
        return self.__module__ + "." + self.__class__.__name__ + "()"

    # Override the following methods in subclass:

    def make_blocks(self):
        """Return a list of :class:`TranslatedBlockType` objects, which will be
        the value of the :attr:`blocks` property.

        This function is only called once.

        """
        raise NotImplementedError

    def load(self, path):
        """Load a project from a file with this format.

        :attr:`Project.path` will be set later. :attr:`Project.name` will be
        set to the filename of ``path`` if unset.

        The file at ``path`` is not guaranteed to exist.

        :param path: Path to the file, including the plugin's extension.
        :returns: :class:`Project`

        """
        raise NotImplementedError

    def save(self, path, project):
        """Save a project to a file with this format.

        :param path: Path to the file, including the plugin's extension.
        :param project: a :class:`Project`

        """
        raise NotImplementedError


class Kurt(object):
    """The Kurt file format loader.

    This class manages the registering and selection of file formats. Used by
    :class:`Project`.
    """

    plugins = OrderedDict()

    blocks = []

    @classmethod
    def register(cls, plugin):
        """Register a new :class:`KurtPlugin`.

        Once registered, the plugin can be used by :class:`Project`, when:

        * :attr:`Project.load` sees a file with the right extension

        * :attr:`Project.convert` is called with the format as a parameter

        """
        cls.plugins[plugin.name] = plugin

        # make features
        plugin.features = map(Feature.get, plugin.features)

        # fix blocks
        for tbt in plugin.blocks:
            if tbt:
                tbt.format = plugin.name

        # add blocks
        new_blocks = filter(None, plugin.blocks)
        for tbt in new_blocks:
            for bt in cls.blocks:
                if (bt.has_command(tbt.command) or
                        bt.has_command(tbt._match)):
                    bt._add_translation(plugin.name, tbt)
                    break
            else:
                if tbt._match:
                    raise ValueError, "Couldn't match %r" % tbt._match
                cls.blocks.append(kurt.BlockType(tbt))

    @classmethod
    def get_plugin(cls, name=None, **kwargs):
        """Returns the first format plugin whose attributes match kwargs.

        For example::

            get_plugin(extension="scratch14")

        Will return the :class:`KurtPlugin` whose :attr:`extension
        <KurtPlugin.extension>` attribute is ``"scratch14"``.

        The :attr:`name <KurtPlugin.name>` is used as the ``format`` parameter
        to :attr:`Project.load` and :attr:`Project.save`.

        :raises: :class:`ValueError` if the format doesn't exist.

        :returns: :class:`KurtPlugin`

        """
        if isinstance(name, KurtPlugin):
            return name

        if 'extension' in kwargs:
            kwargs['extension'] = kwargs['extension'].lower()
        if name:
            kwargs["name"] = name
        if not kwargs:
            raise ValueError, "No arguments"

        for plugin in cls.plugins.values():
            for name in kwargs:
                if getattr(plugin, name) != kwargs[name]:
                    break
            else:
                return plugin

        raise ValueError, "Unknown format %r" % kwargs

    @classmethod
    def block_by_command(cls, command):
        """Return the block with the given :attr:`command`.

        Returns None if the block is not found.

        """
        for block in cls.blocks:
            if block.has_command(command):
                return block

    @classmethod
    def blocks_by_text(cls, text):
        """Return a list of blocks matching the given :attr:`text`.

        Capitalisation and spaces are ignored.

        """
        text = kurt.BlockType._strip_text(text)
        matches = []
        for block in cls.blocks:
            for tbt in block._translations.values():
                if tbt.stripped_text == text:
                    matches.append(block)
                    break
        return matches



#-- Features --#

class Feature(object):
    """A format feature that a plugin supports."""

    FEATURES = {}

    @classmethod
    def get(cls, name):
        if isinstance(name, Feature):
            return name
        return cls.FEATURES[name]

    def __init__(self, name, description):
        self.name = name
        self.description = description
        Feature.FEATURES[name] = self

    def __repr__(self):
        return "<Feature(%s)>" % self.name

    def __eq__(self, other):
        if isinstance(other, basestring):
            return self.name == other
        return self is other

    def workaround(self, project):
        if False: yield

    def __call__(self, f):
        self.workaround = f


@Feature("Vector Images",
        """Allow vector format (SVG) image files for costumes.""")
def _workaround(project):
    """Replace vector images with fake ones."""
    RED = (255, 0, 0)
    PLACEHOLDER = kurt.Image.new((32, 32), RED)
    for scriptable in [project.stage] + project.sprites:
        for costume in scriptable.costumes:
            if costume.image.format == "SVG":
                yield "%s - %s" % (scriptable.name, costume.name)
                costume.image = PLACEHOLDER

@Feature("Stage-specific Variables",
        """Can have stage-specific variables and lists, in addition to global
        variables and lists (which are stored on the :class:`Project`).""")
def _workaround(project):
    """Make Stage-specific variables global (move them to Project)."""
    for (name, var) in project.stage.variables.items():
        yield "variable %s" % name
    for (name, _list) in project.stage.lists.items():
        yield "list %s" % name
    project.variables.update(project.stage.variables)
    project.lists.update(project.stage.lists)
    project.stage.variables = {}
    project.stage.lists = {}

Feature("Custom Blocks", """Blocks accept :class:`CustomBlockType` objects for
        their :attr:`type`.""")

del _workaround



#-- Convert Blocks --#

def block_workaround(bt, workaround):
    if isinstance(workaround, kurt.Block):
        w = workaround
        workaround = lambda block: w.copy()
    else:
        assert callable(workaround)
    bt = kurt.BlockType.get(bt)
    bt._add_workaround(workaround)
