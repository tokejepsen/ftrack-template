import lucidity


class Template(lucidity.Template):

    _hash_code = "_HASH_"

    def _convert(self, match, placeholder_count):
        '''Return a regular expression to represent *match*.

        *placeholder_count* should be a `defaultdict(int)` that will be used to
        store counts of unique placeholder names.

        '''
        placeholder_name = match.group('placeholder')

        placeholder_name = placeholder_name.replace("#", self._hash_code)

        # Support at symbol (@) as referenced template indicator. Currently,
        # this symbol not a valid character for a group name in the standard
        # Python regex library. Rather than rewrite or monkey patch the library
        # work around the restriction with a unique identifier.
        placeholder_name = placeholder_name.replace('@', self._at_code)

        # Support period (.) as nested key indicator. Currently, a period is
        # not a valid character for a group name in the standard Python regex
        # library. Rather than rewrite or monkey patch the library work around
        # the restriction with a unique identifier.
        placeholder_name = placeholder_name.replace('.', self._period_code)

        # The re module does not support duplicate group names. To support
        # duplicate placeholder names in templates add a unique count to the
        # regular expression group name and strip it later during parse.
        placeholder_count[placeholder_name] += 1
        placeholder_name += '{0:03d}'.format(
            placeholder_count[placeholder_name]
        )

        expression = match.group('expression')
        if expression is None:
            expression = self._default_placeholder_expression

        # Un-escape potentially escaped characters in expression.
        expression = expression.replace('\{', '{').replace('\}', '}')

        return r'(?P<{0}>{1})'.format(placeholder_name, expression)
