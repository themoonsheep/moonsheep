def equal_compare(a, b):
    return a == b


class BaseVerifier:
    def __init__(self, field_name=None):
        self.field_name = field_name


class NaiveEqualsVerifier(BaseVerifier):
    def __call__(self, *args, **kwargs):
        first_elem = args[0]
        outcome = 1
        for obj in args:
            if not equal_compare(first_elem, obj):
                outcome = 0
        return first_elem, outcome


class EqualsVerifier(BaseVerifier):
    def __call__(self, *args, **kwargs):
        result_dict = {}
        for obj in args[0]:
            if obj in result_dict:
                result_dict[obj] += 1
            else:
                result_dict[obj] = 1

        import operator
        best_match = max(result_dict.items(), key=operator.itemgetter(1))[0]

        return best_match, result_dict[best_match]


class UnorderedSetVerifier(BaseVerifier):
    def __call__(self, *args, **kwargs):
        # return [1,2,3,4]
        pass


class DateVerifier(BaseVerifier):
    def __call__(self, *args, **kwargs):
        # return a == b
        pass


class NumbersVerifier(BaseVerifier):
    def __call__(self, *args, **kwargs):
        # return a == b
        pass


class TextVerifier(BaseVerifier):
    def __call__(self, *args, **kwargs):
        # return a == b
        pass
