# Copyright (C) 2026 Mengjia Sun
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. It is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License (LICENSE) for more details.

"""sllmwiki: the Structural LLM Wiki's code. The plugin's instructions run it as
`sllmwiki <command>`; a wiki's GitHub Actions run it from this repository at the tag."""

import os

__version__ = '1.3.0'  # the plugin's version too (.claude-plugin/plugin.json); a test keeps them equal

TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')  # what init installs, the narrative templates, the book's
