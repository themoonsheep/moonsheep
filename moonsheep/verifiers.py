import collections
import inspect
import statistics
import operator
from typing import List

MIN_CONFIDENCE = 1


def max_index(values: list) -> (int, any):
    """
    Return the index and the value of a maximal item
    :param values:
    :return (int, any): (index, value)
    """
    return max(values.items(), key=operator.itemgetter(1))


def equals(values: list):
    result_dict = {}
    for obj in values:
        if obj in result_dict:
            result_dict[obj] += 1
        else:
            result_dict[obj] = 1

    best_match = max(result_dict.items(), key=operator.itemgetter(1))[0]
    confidence = result_dict[best_match] / len(values)
    return best_match, confidence


class TaskVerifier:
    """
    Operates in a context of a Task defining nested fields which verification can be overriden
    by defining verify_{field} methods.
    """
    def __init__(self, task, model_prefix):
        self.task = task
        self.model_prefix = model_prefix + '__'

    def verifier_for(self, value_type):
        if value_type is dict:
            verifier = DEFAULT_DICT_VERIFIER
        elif value_type is list:
            verifier = DEFAULT_LIST_VERIFIER
        else:
            # basic type I guess
            verifier = DEFAULT_BASIC_VERIFIER_METHOD

        return verifier


class DictVerifier(TaskVerifier):
    def __call__(self, entries: list):
        """
        Verify independently all fields in a dict.

        :param entries: list containing taskrun dictionaries
        :type entries: list
        :return: dictionary containing tuples of verified fields
        """
        field_entries = collections.defaultdict(list)
        results_dict = {}
        confidences_list = []

        for entry in entries:
            for fld, values in entry.items():
                field_entries[fld].append(values)

        for fld, values in field_entries.items():
            # if no values, empty array
            if not values:
                # TODO should we return empty here?
                continue

            # Handle custom verification methods
            default_verifier = self.verifier_for(type(values[0]))
            verifier = getattr(self, "verify_" + self.model_prefix + fld, default_verifier)

            # Create instance of verifier class if needed
            if inspect.isclass(verifier):
                verifier = verifier(self.task, model_prefix=self.model_prefix + fld)

            value, confidence = verifier(values)
            results_dict[fld] = value
            confidences_list.append(confidence)

        overall_confidence = min(confidences_list)
        return results_dict, overall_confidence


class OrderedListVerifier(TaskVerifier):
    def __init__(self, task, model_prefix, sort_by=None):
        super().__init__(task, model_prefix)

    def __call__(self, entries: List[List]):
        entries.sort(key = lambda s: len(s))
        verifier = self.verifier_for(type(entries[0][0]))

        # Create instance of verifier class if needed
        if inspect.isclass(verifier):
            verifier = verifier(self.task, model_prefix=self.model_prefix)

        results_list = []
        confidences_list = []
        item_counts = [len(entry) for entry in entries]

        # TODO a quite dumb way to cross-check
        for i in range(item_counts[0]):
            values_at_i = []
            for entry in entries:
                if i < len(entry):
                    values_at_i.append(entry[i])

            value, confidence = verifier(values_at_i)
            results_list.append(value)
            confidences_list.append(confidence)

        minmax = max(item_counts) - min(item_counts)
        if minmax == 0:
            counts_confidence = 1
        else:
            counts_confidence = max(0, 1 - statistics.stdev(item_counts) / minmax * 2)

        overall_confidence = min(counts_confidence, min(confidences_list))

        return results_list, overall_confidence


DEFAULT_DICT_VERIFIER = DictVerifier
DEFAULT_LIST_VERIFIER = OrderedListVerifier
DEFAULT_BASIC_VERIFIER_METHOD = equals
