# -*- coding: utf-8 -*-
"""Provides parser for HGVS strings and HGVS-related conceptual
components, such as intronic-offset coordiates

"""

from __future__ import absolute_import, division, print_function, unicode_literals

import copy
import logging
import re

import bioutils.sequences
import ometa.runtime
import parsley
from pkg_resources import resource_filename

import hgvs.edit

# The following imports are referenced by fully-qualified name in the
# hgvs grammar.
import hgvs.enums
import hgvs.hgvsposition
import hgvs.location
import hgvs.posedit
import hgvs.sequencevariant
from hgvs.exceptions import HGVSParseError
from hgvs.generated.hgvs_grammar import createParserClass


class Parser(object):
    """Provides comprehensive parsing of HGVS variant strings (*i.e.*,
    variants represented according to the Human Genome Variation
    Society recommendations) into Python representations.  The class
    wraps a Parsing Expression Grammar, exposing rules of that grammar
    as methods (prefixed with `parse_`) that parse an input string
    according to the rule.  The class exposes all rules, so that it's
    possible to parse both full variant representations as well as
    components, like so:

    >>> hp = Parser()
    >>> v = hp.parse_hgvs_variant("NM_01234.5:c.22+1A>T")
    >>> v
    SequenceVariant(ac=NM_01234.5, type=c, posedit=22+1A>T, gene=None)
    >>> v.posedit.pos
    BaseOffsetInterval(start=22+1, end=22+1, uncertain=False)
    >>> i = hp.parse_c_interval("22+1")
    >>> i
    BaseOffsetInterval(start=22+1, end=22+1, uncertain=False)

    The `parse_hgvs_variant` and `parse_c_interval` methods correspond
    to the `hgvs_variant` and `c_interval rules` in the grammar,
    respectively.

    As a convenience, the Parser provides the `parse` method as a
    shorthand for `parse_hgvs_variant`:
    >>> v = hp.parse("NM_01234.5:c.22+1A>T")
    >>> v
    SequenceVariant(ac=NM_01234.5, type=c, posedit=22+1A>T, gene=None)

    Because the methods are generated on-the-fly and depend on the
    grammar that is loaded at runtime, a full list of methods is not
    available in the documentation.  However, the list of
    rules/methods is available via the `rules` instance variable.

    A few notable methods are listed below:

    `parse_hgvs_variant()` parses any valid HGVS string supported by the grammar.

      >>> hp.parse_hgvs_variant("NM_01234.5:c.22+1A>T")
      SequenceVariant(ac=NM_01234.5, type=c, posedit=22+1A>T, gene=None)
      >>> hp.parse_hgvs_variant("NP_012345.6:p.Ala22Trp")
      SequenceVariant(ac=NP_012345.6, type=p, posedit=Ala22Trp, gene=None)

    The `hgvs_variant` rule iteratively attempts parsing using the
    major classes of HGVS variants. For slight improvements in
    efficiency, those rules may be invoked directly:

      >>> hp.parse_p_variant("NP_012345.6:p.Ala22Trp")
      SequenceVariant(ac=NP_012345.6, type=p, posedit=Ala22Trp, gene=None)

    Similarly, components of the underlying structure may be parsed
    directly as well:

      >>> hp.parse_c_posedit("22+1A>T")
      PosEdit(pos=22+1, edit=A>T, uncertain=False)
      >>> hp.parse_c_interval("22+1")
      BaseOffsetInterval(start=22+1, end=22+1, uncertain=False)

    """

    def __init__(self, grammar_fn=None, expose_all_rules=False):
        bindings = {"hgvs": hgvs, "bioutils": bioutils, "copy": copy}
        if grammar_fn is None:
            self._grammar = parsley.wrapGrammar(
                createParserClass(ometa.runtime.OMetaGrammarBase, bindings)
            )
        else:
            # Still allow other grammars if you want
            with open(grammar_fn, "r") as grammar_file:
                self._grammar = parsley.makeGrammar(grammar_file.read(), bindings)
        self._logger = logging.getLogger(__name__)
        self._expose_rule_functions(expose_all_rules)

    def parse_hgvs_variant_explain ( self, v ):
        """parse HGVS variant `v`, with explanation (return type varies by result)

        :param str v: an HGVS-formatted variant as a string

        """
        try:
            return self.parse_hgvs_variant( v )
        except HGVSParseError as exc:
            match = re.search( "char (\d+): expected (.+)$", exc.args[ 0 ] )

            if (not match):
                msg = "[{v}] bombed, cannot handle this error yet: {exc}".format( v = v, exc = exc )
                raise exc( msg )  # pass the exception through (todo: check syntax)

            char_pos = int( match.group( 1 ) )
            expected_str = match.group( 2 )
            # print("got match at [{pos}]".format(pos=char_pos))

            # try to handle diff error types based on the expected_str
            if (expected_str == "EOF"):
                # examples that trigger this error are often caused by a single char, so skip it
                # todo: consider whether to try to identify offending char(s) dynamically
                part1, part2 = v[ :char_pos ], v[ char_pos + 1: ]
                part2 = part2.strip()  # part1 is likely valid, but part2 might have whitespace
                print( "got an EOF, creating [{part1}], [{part2}]".format( part1 = part1, part2 = part2 ) )

                # try to parse each half separately
                v1 = self.parse( part1, explain = True )
                if (v1):
                    print( "rescued and parsed part1:", v1 )
                v2 = self.parse( part2, explain = True )
                if (v2):
                    print( "rescued and parsed part2:", v2 )

            elif (expected_str == "a digit"):
                # checking for 'p.' and '{AA}{\d+}{AA}'
                m = re.search( "p\..*([a-zA-Z][a-zA-Z]{2}?)(\d+)([a-zA-Z][a-zA-Z]{2}?)", exc.args[ 0 ],
                               flags = re.IGNORECASE )
                if (m):
                    print(
                        "chunk [{v}] looks like a p. string: [p.][{g1}][{g2}][{g3}]".format( v = v, g1 = m.group( 1 ),
                                                                                             g2 = m.group( 2 ),
                                                                                             g3 = m.group( 3 ) ) )

            else:
                print( "got [{v}], expected [{s}]".format( v = v, s = expected_str ) )

    def parse ( self, v, explain = False ):
        """parse HGVS variant `v`, returning a SequenceVariant

        :param str v: an HGVS-formatted variant as a string
        :param bool explain: flag to enable/disable explain mode
        :rtype: SequenceVariant

        """
        if (explain):
            return self.parse_hgvs_variant_explain( v )

        return self.parse_hgvs_variant( v )

    def _expose_rule_functions(self, expose_all_rules=False):
        """add parse functions for public grammar rules

        Defines a function for each public grammar rule, based on
        introspecting the grammar. For example, the `c_interval` rule
        is exposed as a method `parse_c_interval` and used like this::

          Parser.parse_c_interval('26+2_57-3') -> Interval(...)

        """

        def make_parse_rule_function(rule_name):
            "builds a wrapper function that parses a string with the specified rule"

            def rule_fxn(s):
                try:
                    return self._grammar(s).__getattr__(rule_name)()
                except ometa.runtime.ParseError as exc:
                    raise HGVSParseError(
                        "{s}: char {exc.position}: {reason}".format(
                            s=s, exc=exc, reason=exc.formatReason()
                        )
                    )

            rule_fxn.__doc__ = "parse string s using `%s' rule" % rule_name
            return rule_fxn

        exposed_rule_re = re.compile(
            r"hgvs_(variant|position)|(c|g|m|n|p|r)"
            r"_(edit|hgvs_position|interval|pos|posedit|variant)"
        )
        exposed_rules = [
            m.replace("rule_", "")
            for m in dir(self._grammar._grammarClass)
            if m.startswith("rule_")
        ]
        if not expose_all_rules:
            exposed_rules = [
                rule_name for rule_name in exposed_rules if exposed_rule_re.match(rule_name)
            ]
        for rule_name in exposed_rules:
            att_name = "parse_" + rule_name
            rule_fxn = make_parse_rule_function(rule_name)
            self.__setattr__(att_name, rule_fxn)
        self._logger.debug(
            "Exposed {n} rules ({rules})".format(
                n=len(exposed_rules), rules=", ".join(exposed_rules)
            )
        )


# <LICENSE>
# Copyright 2018 HGVS Contributors (https://github.com/biocommons/hgvs)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# </LICENSE>
