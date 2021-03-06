from __future__ import print_function
import sys
import math
import argparse
import csv
from hew.structures.node import Node
from collections import defaultdict


class C45(object):
    """
    Credit for this goes to
        Jeremy Kun -> https://github.com/j2kun/decision-trees
    and Timothy Trukhanov -> https://github.com/geerk/C45algorithm
    """

    def __init__(self, dictionaryOfLists, validate=True):
        self.columnSet = dictionaryOfLists
        self.partitionKey = None
        self.partitionValue = None
        self.depth = 1
        self.maxDepth = 100
        if validate:
            self._validate()

    def _validate(self):
        assert isinstance(self.columnSet, dict)
        assert len(self.columnSet)
        size = self.size()
        for k, v in self.columnSet.items():
            assert k
            assert isinstance(k, str)
            assert len(v) == size

    #--------------------------------------------------------------------------

    @classmethod
    def fromTable(cls, arrayOfDictionaries):
        T = defaultdict(list)
        for row in arrayOfDictionaries:
            for col in row:
                T[col].append(row[col])
        return C45(T)

    #--------------------------------------------------------------------------

    def rule(self):
        if not self.partitionKey:
            return ''
        return '{0}={1}'.format(self.partitionKey, self.partitionValue)

    def size(self):
        col = list(self.columnSet.keys())[0]
        return len(self.columnSet[col])

    def flen(self, col):
        """ Returns the length of column _col_ as a float.
        """
        return float(len(self.columnSet[col]))

    def uniques(self, col):
        return list(set(self.columnSet[col]))

    def frequency(self, col, v):
        """ Returns counts of variant _v_ in column _col_.
        """
        return self.columnSet[col].count(v)

    def isHomogeneous(self, col):
        """ Returns True if all values in _col_ are equal and False otherwise.
        """
        t0 = self.columnSet[col][0]
        for i in self.columnSet[col]:
            if i != t0:
                return False
        return True

    def get_indexes(self, col, v):
        """ Returns indexes of values _v_ in column _col_.
        """
        return {i for i, x in enumerate(self.columnSet[col]) if x == v}

    def get_values(self, col, indexes):
        """ Returns values of _indexes_ in column _col_
        """
        column = self.columnSet[col]
        return [column[i] for i in range(len(column)) if i in indexes]

    #--------------------------------------------------------------------------

    def info(self, res_col):
        """ Calculates the entropy where res_col column = _res_col_.
        """
        s = 0  # sum
        result_len = self.flen(res_col)
        for v in self.uniques(res_col):
            p = self.frequency(res_col, v) / result_len
            s += p * math.log(p, 2)
        return -s

    def infox(self, col, res_col):
        """ Calculates the entropy of the after dividing it on the subtables
            by column _col_.
        """
        s = 0  # sum
        for subt in self.partitionOnFeature(col):
            s += (subt.flen(col) / self.flen(col)) * subt.info(res_col)
        return s

    def gain(self, x, res_col):
        """ The criterion for selecting attributes for splitting.
        """
        return self.info(res_col) - self.infox(x, res_col)

    #--------------------------------------------------------------------------

    def buildPartition(self, col, v):
        idxs = self.get_indexes(col, v)
        p = {k: [x for i, x in enumerate(v) if i in idxs]
             for k, v in self.columnSet.items()}

        sub = C45(p, False)
        sub.depth = self.depth + 1
        sub.maxDepth = self.maxDepth
        sub.partitionKey = col
        sub.partitionValue = v
        return sub

    def partitionOnFeature(self, col):
        """ Returns subtables divided by values of the column _col_.
        """
        return [self.buildPartition(col, v) for v in self.uniques(col)]

    #--------------------------------------------------------------------------

    def buildTree(self, res_col):
        tree = Node(self)

        if self.depth > self.maxDepth:
            return tree

        gain_list = [(k, self.gain(k, res_col))
                     for k in self.columnSet if k != res_col]
        if not gain_list:
            return tree

        col = max(gain_list, key=lambda x: x[1])[0]
        for subt in self.partitionOnFeature(col):
            if subt.isHomogeneous(res_col):
                tree.add(Node(subt))
            else:
                del subt.columnSet[col]
                tree.add(subt.buildTree(res_col))
        return tree

    @classmethod
    def outputDecision(cls, node, res_col, predicates, fout):
        c45 = node.data
        rule = c45.rule()
        if rule:
            predicates.append(rule)

        if not node.children:
            target = "~".join(set(c45.uniques(res_col)))
            line = "{0}\t{1}\t{2}={3}\t{4}".format(c45.size(), len(predicates),
                                                   res_col, target,
                                                   ' & '.join(predicates))
            print(line, file=fout)
        else:
            for c in node.children:
                cls.outputDecision(c, res_col, list(predicates), fout)

    @classmethod
    def makeDecisionTree(cls, arrayOfDictionaries, res_col, fout, maxDepth=20):
        """ Returns a tree of decisions from _arrayOfDictionaries_
            _res_col_ must be the name of field that contains the target result
        """
        root = C45.fromTable(arrayOfDictionaries)
        if res_col not in root.columnSet:
            print(res_col, 'is not a valid column. Exiting.', file=sys.stderr)
            return

        root.maxDepth = maxDepth
        a = root.buildTree(res_col)
        print('Count\tPath_Length\tResult\tPredicates', file=fout)
        C45.outputDecision(a, res_col, [], fout)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def buildArgParser():
    description = 'Build a decision tree from a table of features'
    p = argparse.ArgumentParser(description=description)
    p.add_argument('input', metavar='inputFileName',
                   help='the file to process')
    p.add_argument('target',  metavar='targetColumn',
                   help='the column that holds the expected result')
    p.add_argument('output', nargs='?', metavar='outputFileName',
                   default='decision.txt',
                   help='the name of the file that will hold the results')
    p.add_argument('--max', nargs='?', action='store', type=int,
                   dest='maxDepth', default=20,
                   help='the maximum depth the features will split')

    return p

if __name__ == '__main__':
    parser = buildArgParser()
    args = parser.parse_args()

    with open(args.input, 'r') as f:
        reader = csv.DictReader(f, dialect=csv.excel_tab)
        data = [row for row in reader]

    with open(args.output, 'w') as f:
        C45.makeDecisionTree(data, args.target, f, args.maxDepth)
