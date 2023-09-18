"""Represents ...

"""


class HGVSExplained(object):
    """Represents ...

    TODO: write docs

    """

    def __init__(self, *, orig_var_string, hgvs_obj=None, hgvs_parser_exc=None, hgvs_error_type=None ):
        self.orig_var_string = orig_var_string
        self.hgvs_obj = hgvs_obj
        self.hgvs_parser_exc = hgvs_parser_exc
        self.hgvs_error_type = hgvs_error_type
        self.parse_explain = [] # array of HGVSExplained

        # if orig var string is valid hgvs
        #   hgvs_obj will be populated
        # else
        #   hgvs_parser_exception and hgvs_error_type will be populated
        #   if attempt rescue, then parse_explain also will be populated

    def add_explained(self, *expl_list):
        for e in expl_list:
            assert( isinstance(e, HGVSExplained) )
            self.parse_explain.append(e)

    def as_json( self ):
        json_str = json.dumps(self, indent=2)
        return json_str
