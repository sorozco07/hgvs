"""Provides parser for HGVS strings and HGVS-related conceptual
components, such as intronic-offset coordiates. Attempts to identify
and provide suggestions for components that do not strictly conform
to the official HGVS spec (when initial parsing throws an exception).

"""

import re
from hgvs.hgvsexplained import HGVSExplained
import logging
from hgvs.exceptions import HGVSParseError

class ParserExplainer(object):
    """Provides ...

    >>> hpe = ParserExplainer("...")

    TODO: write docs

    """

    def __init__(self, hgvs_parser):
        self._hgvs_parser = hgvs_parser

    def parse_hgvs_variant_explain( self, v ):
        """parse HGVS variant `v`, with explanation (return type varies by result)

        :param str v: an HGVS-formatted variant as a string

        """
        self._orig_var_string = v

        try:
            print("trying to parse [{v}]".format(v=v))
            hgvs = self._hgvs_parser.parse_hgvs_variant(v)
            print("got a {t} object and putting it in hgvs_obj".format(t=type(hgvs)))
            return HGVSExplained( orig_var_string=v, hgvs_obj=hgvs )
        except HGVSParseError as exc:
            print("HGVS parsing failed, calling _explain()")
            hgvs_e = HGVSExplained( orig_var_string=v, hgvs_parser_exc=exc, hgvs_error_type='TBD' )
            expl_list = self._explain(v, exc) # this should return a list of HGVSExplained objects
            print("got results from explaining [{v}], [{n}] elements in list".format(v=v, n=len(expl_list)))
            hgvs_e.add_explained( *expl_list )
            return hgvs_e

    # handles exc, chunk-ifies, calls parse_hgvs_variant_explain() on chunks, returns list of HGVSExplained objects
    def _explain(self, v, exc):
        match = re.search( "char (\d+): expected (.+)$", exc.args[0] )

        if( not match ):
            msg = "[{v}] bombed, cannot handle this error yet: {exc}".format(v=v, exc=exc)
            raise exc( msg ) # pass the exception through (todo: check syntax)

        char_pos = int(match.group(1))
        expected_str = match.group(2)
    
        if(expected_str == "EOF" ):
            # This error is generated when the first part of an expression is valid but the string
            # continues and contains more characters than the grammar rules can handle.
            # Splitting the input string into 2 parts, then re-parsing each. The first is likely
            # to be a valid HGVS expression, while the latter portion is unlikely to be valid.
            part1, part2 = v[:char_pos], v[char_pos+1:]
            part2 = part2.strip()
            print( "got an EOF, creating [{part1}], [{part2}]".format(part1=part1, part2=part2))

            # try to parse each half separately
            results = []
            for part in ( part1, part2):
                result_obj = self.parse_hgvs_variant_explain( part )
                results.append(result_obj)

            return results

        elif( expected_str == "a digit" ):
            # checking for 'p.' and '{AA}{\d+}{AA}'
            m = re.search( "p\..*([a-zA-Z][a-zA-Z]{2}?)(\d+)([a-zA-Z][a-zA-Z]{2}?)", exc.args[0], flags=re.IGNORECASE )
            if( m ):
                print("chunk [{v}] looks like a p. string: [p.][{g1}][{g2}][{g3}]".format(v=v, g1=m.group(1), g2=m.group(2), g3=m.group(3) ) )

            hgvs_e = HGVSExplained( orig_var_string=v, hgvs_parser_exc=exc, hgvs_error_type='looks like a p.')
            return [ hgvs_e ]
        
        elif re.search("one of .+ or a digit$", expected_str):
            print("'{l}' is not a valid character. Invalid character at position {c} in string {v}.".format(c=char_pos, v=v, l = v[char_pos]))
            
            # c_variant_p_variant = r"^(NM.*)(NP.+)"
            c_variant_p_variant = r"^(NM[^,]+), (NP.+)"
            if m := re.search(c_variant_p_variant, v):
                coding = m.group(1)
                protein = m.group(2)
                print("Received two groups [{c}, {p}] but expecting input only expected one.".format(c=coding, p = protein))
                
                # try to parse each half separately
                coding_parse = self._hgvs_parser.parse( coding, explain=True )
                if( coding_parse ):
                    print("rescued and parsed part1:", coding)
                protein_parse = self._hgvs_parser.parse( protein, explain=True )
                if( protein_parse ):
                    print("rescued and parsed part2:", protein)
            return 'test2'
            
        else:
            print("got [{v}], expected [{s}]".format(v=v, s=expected_str) )
            return 'test3'
    
