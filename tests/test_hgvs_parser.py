# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import pprint
import unittest

import pytest

import hgvs.parser
from hgvs.exceptions import HGVSParseError


def test_parser_variants_with_gene_names(parser):
    assert parser.parse("NM_01234.5(BOGUS):c.22+1A>T")

    with pytest.raises(hgvs.exceptions.HGVSParseError):
        parser.parse("NM_01234.5(1BOGUS):c.22+1A>T")


class Test_Parser(unittest.TestCase):
    longMessage = True

    @classmethod
    def setUpClass(cls):
        cls.parser = hgvs.parser.Parser()

    def test_parser_parse_shorthand(self):
        v = "NM_01234.5:c.22+1A>T"
        assert self.parser.parse_hgvs_variant(v) == self.parser.parse(v)

    def test_parser_gauntlet(self):
        fn = os.path.join(os.path.dirname(__file__), "data", "gauntlet")
        for var in open(fn, "r"):
            var = var.strip()
            if var.startswith("#") or var == "":
                continue
            v = self.parser.parse_hgvs_variant(var)
            self.assertEqual(
                var,
                v.format(conf={"max_ref_length": None}),
                "parse-format roundtrip failed:" + pprint.pformat(v.posedit),
            )

    @pytest.mark.quick
    def test_parser_reject(self):
        fn = os.path.join(os.path.dirname(__file__), "data", "reject")
        for var in open(fn, "r"):
            var, msg = var.strip().split("\t")
            if var.startswith("#") or var == "":
                continue
            with self.assertRaises(HGVSParseError):
                self.parser.parse_hgvs_variant(var)
                self.assertTrue(False, msg="expected HGVSParseError: %s (%s)" % (var, msg))

    @pytest.mark.quick
    def test_parser_posedit_special(self):
        # See note in grammar about parsing p.=, p.?, and p.0
        self.assertEqual(str(self.parser.parse_p_posedit("0")), "0")
        self.assertEqual(str(self.parser.parse_p_posedit("0?")), "0?")
        # self.assertEqual( str(self.parser.parse_p_posedit("(0)")), "0?" )

        self.assertIsNone(self.parser.parse_p_posedit("?"))

        self.assertEqual(str(self.parser.parse_p_posedit("=")), "=")
        # self.assertEqual( str(self.parser.parse_p_posedit("=?")), "(=)" )
        self.assertEqual(str(self.parser.parse_p_posedit("(=)")), "(=)")

    @pytest.mark.quick
    def test_generation_timetamp(self):
        """ We generate Python code from the OMeta grammar
            This test checks that the generated file is older than the source grammar """

        script_path = os.path.realpath(__file__)
        script_dir = os.path.dirname(script_path)
        hgvs_base_dir = os.path.dirname(script_dir)
        grammar_filename = "src/hgvs/_data/hgvs.pymeta"
        generated_filename = "src/hgvs/generated/hgvs_grammar.py"

        grammar_mtime = os.path.getmtime(os.path.join(hgvs_base_dir, grammar_filename))
        generated_mtime = os.path.getmtime(os.path.join(hgvs_base_dir, generated_filename))
        msg = "OMeta source '{grammar_filename}' is more recently modified than " \
              "generated Python code '{generated_filename}'. You need to run " \
              "'sbin/generate_parser.py' ".format(grammar_filename=grammar_filename,
                                                  generated_filename=generated_filename)
        self.assertGreater(generated_mtime, grammar_mtime, msg)


if __name__ == "__main__":
    unittest.main()

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
