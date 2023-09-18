"""Provides parser for HGVS strings and HGVS-related conceptual
components, such as intronic-offset coordiates. Attempts to identify
and provide suggestions for components that do not strictly conform
to the official HGVS spec (when initial parsing throws an exception).

"""

import re
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
            return self._hgvs_parser.parse_hgvs_variant(v)
        except HGVSParseError as exc:
            self._explain(v, exc)
        
    def _explain(self, v, exc):
        match = re.search( "char (\d+): expected (.+)$", exc.args[0] )
        
        if( not match ):
            msg = "[{v}] bombed, cannot handle this error yet: {exc}".format(v=v, exc=exc)
            raise exc( msg ) # pass the exception through (todo: check syntax)

        char_pos = int(match.group(1))
        expected_str = match.group(2)
    
        if(expected_str == "EOF" ):
            part1, part2 = v[:char_pos], v[char_pos+1:]
            part2 = part2.strip() # part1 is likely valid, but part2 might have whitespace
            print( "got an EOF, creating [{part1}], [{part2}]".format(part1=part1, part2=part2))

            # try to parse each half separately
            v1 = self._hgvs_parser.parse( part1, explain=True )
            if( v1 ):
                print("rescued and parsed part1:", v1)
            v2 = self._hgvs_parser.parse( part2, explain=True )
            if( v2 ):
                print("rescued and parsed part2:", v2)

        elif( expected_str == "a digit" ):
            # checking for 'p.' and '{AA}{\d+}{AA}'
            m = re.search( "p\..*([a-zA-Z][a-zA-Z]{2}?)(\d+)([a-zA-Z][a-zA-Z]{2}?)", exc.args[0], flags=re.IGNORECASE )
            if( m ):
                print("chunk [{v}] looks like a p. string: [p.][{g1}][{g2}][{g3}]".format(v=v, g1=m.group(1), g2=m.group(2), g3=m.group(3) ) )
        
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
            
        else:
            print("got [{v}], expected [{s}]".format(v=v, s=expected_str) )
