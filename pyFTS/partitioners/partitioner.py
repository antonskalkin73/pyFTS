from pyFTS.common import FuzzySet, Membership
import numpy as np
from scipy.spatial import KDTree
import warnings


class Partitioner(object):
    """
    Universe of Discourse partitioner. Split data on several fuzzy sets
    """

    def __init__(self, **kwargs):
        """
        Universe of Discourse partitioner scheme. Split data on several fuzzy sets
        """
        self.name : str = kwargs.get('name',"")
        """partitioner name"""
        self.partitions : int = kwargs.get('npart', 10)
        """The number of universe of discourse partitions, i.e., the number of fuzzy sets that will be created"""
        self.sets : dict = {}
        """The fuzzy sets dictionary"""
        self.membership_function = kwargs.get('func', Membership.trimf)
        """Fuzzy membership function (pyFTS.common.Membership)"""
        self.setnames : list = kwargs.get('names', None)
        """list of partitions names. If None is given the partitions will be auto named with prefix"""
        self.prefix : str = kwargs.get('prefix', 'A')
        """prefix of auto generated partition names"""
        self.transformation = kwargs.get('transformation', None)
        """data transformation to be applied on data"""
        self.indexer = kwargs.get('indexer', None)
        self.variable = kwargs.get('variable', None)
        """In a multivariate context, the variable that contains this partitioner"""
        self.type : str = kwargs.get('type', 'common')
        """The type of fuzzy sets that are generated by this partitioner"""
        self.ordered_sets : list = None
        """A ordered list of the fuzzy sets names, sorted by their middle point"""
        self.kdtree : KDTree = None
        """A spatial index to help in fuzzyfication"""
        self.margin : float = kwargs.get("margin", 0.1)
        """The upper and lower exceeding margins for the known UoD. The default value is .1"""
        self.lower_margin : float = kwargs.get("lower_margin", self.margin)
        """Specific lower exceeding margins for the known UoD. The default value is the self.margin parameter"""
        self.upper_margin : float = kwargs.get("lower_margin", self.margin)
        """Specific upper exceeding margins for the known UoD. The default value is the self.margin parameter"""

        if kwargs.get('preprocess',True):

            data = kwargs.get('data',[None])

            if isinstance(data, np.ndarray) and len(data.shape) > 1:
                warnings.warn(f"An ndarray of dimension greater than 1 is used. shape.len(): {len(data.shape)}")

            if self.indexer is not None:
                ndata = self.indexer.get_data(data)
            else:
                ndata = data

            if self.transformation is not None:
                ndata = self.transformation.apply(ndata)
            else:
                ndata = data

            if self.indexer is not None:
                ndata = self.indexer.get_data(ndata)

            _min = np.nanmin(ndata)
            if _min == -np.inf:
                ndata[ndata == -np.inf] = 0
                _min = np.nanmin(ndata)

            self.min = float(_min * (1 + self.lower_margin) if _min < 0 else _min * (1 - self.lower_margin))

            _max = np.nanmax(ndata)
            self.max = float(_max * (1 + self.upper_margin) if _max > 0 else _max * (1 - self.upper_margin))

            self.sets = self.build(ndata)

            self.partitions = len(self.sets)

            if self.ordered_sets is None and self.setnames is not None:
                self.ordered_sets = self.setnames[:len(self.sets)]
            else:
                self.ordered_sets = FuzzySet.set_ordered(self.sets)

            del(ndata)

    def extractor(self,x):
        """Extract a single primitive type from an structured instance"""
        return x

    def build(self, data):
        """
        Perform the partitioning of the Universe of Discourse

        :param data:  training data
        :return: 
        """
        pass

    def get_name(self, counter):
        """
        Find the name of the fuzzy set given its counter id.

        :param counter: The number of the fuzzy set
        :return: String
        """
        return self.prefix + str(counter) if self.setnames is None else self.setnames[counter]

    def lower_set(self):
        """
        Return the fuzzy set on lower bound of the universe of discourse.

        :return: Fuzzy Set
        """
        return self.sets[self.ordered_sets[0]]

    def upper_set(self):
        """
        Return the fuzzy set on upper bound of the universe of discourse.

        :return: Fuzzy Set
        """
        return self.sets[self.ordered_sets[-1]]

    def build_index(self):
        points = []

        #self.index = {}

        for ct, key in enumerate(self.ordered_sets):
            fset = self.sets[key]
            points.append([fset.lower, fset.centroid, fset.upper])
            #self.index[ct] = fset.name

        import sys
        sys.setrecursionlimit(100000)

        self.kdtree = KDTree(points)

        sys.setrecursionlimit(1000)

    def fuzzyfy(self, data, **kwargs):
        """
        Fuzzyfy the input data according to this partitioner fuzzy sets.

        :param data: input value to be fuzzyfied
        :keyword alpha_cut: the minimal membership value to be considered on fuzzyfication (only for mode='sets')
        :keyword method: the fuzzyfication method (fuzzy: all fuzzy memberships, maximum: only the maximum membership)
        :keyword mode: the fuzzyfication mode (sets: return the fuzzy sets names, vector: return a vector with the membership
        values for all fuzzy sets, both: return a list with tuples (fuzzy set, membership value) )

        :returns a list with the fuzzyfied values, depending on the mode
        """

        if isinstance(data, (tuple, list, np.ndarray)):
            ret = []
            for inst in data:
                mv = self.fuzzyfy(inst, **kwargs)
                ret.append(mv)
            return ret

        alpha_cut = kwargs.get('alpha_cut', 0.)
        mode = kwargs.get('mode', 'sets')
        method = kwargs.get('method', 'fuzzy')

        nearest = self.search(data, type='index')
        mv = np.zeros(self.partitions)

        for ix in nearest:
            tmp = self[ix].membership(data)
            mv[ix] = tmp if tmp >= alpha_cut else 0.


        ix = np.ravel(np.argwhere(mv > 0.))

        if ix.size == 0:
            mv[self.check_bounds(data)] = 1.

        if method == 'fuzzy' and mode == 'vector':
            return mv
        elif method == 'fuzzy' and mode == 'sets':
            try:
                ix = np.ravel(np.argwhere(mv > 0.))
                sets = [self.ordered_sets[i] for i in ix if i < self.partitions]
                return sets
            except Exception as ex:
                return None
        elif method == 'maximum' and mode == 'sets':
            mx = max(mv)
            ix = np.ravel(np.argwhere(mv == mx))
            return self.ordered_sets[ix[0]]
        elif mode == 'both':
            ix = np.ravel(np.argwhere(mv > 0.))
            sets = [(self.ordered_sets[i], mv[i]) for i in ix]
            return sets

    def defuzzyfy(self, values, mode='both'):
        if not isinstance(values, list):
            values = [values]

        num = []
        den = []
        for val in values:
            fset = val[0]
            mv = val[1]
            if mode == 'both':
                num.append( self.sets[fset].centroid * mv )
                den.append(mv)
            elif mode == 'sets':
                num.append(self.sets[fset].centroid)
            elif mode == 'vector':
                num.append(self.sets[self.ordered_sets[fset]].centroid * mv)
                den.append(mv)
            else:
                raise Exception('Unknown deffuzyfication mode')

        if mode in ('both','vector'):
            return np.nansum(num) / np.nansum(den)
        else:
            return np.nanmean(num)

    def check_bounds(self, data):
        """
        Check if the input data is outside the known Universe of Discourse and, if it is, round it to the closest
        fuzzy set.

        :param data: input data to be verified
        :return: the index of the closest fuzzy set when data is outside de universe of discourse or None if
        the data is inside the UoD.
        """

        if data < self.min:
            return 0
        elif data > self.max:
            return self.partitions-1

    def search(self, data, **kwargs):
        """
        Perform a search for the nearest fuzzy sets of the point 'data'. This function were designed to work with several
        overlapped fuzzy sets.

        :param data: the value to search for the nearest fuzzy sets
        :param type: the return type: 'index' for the fuzzy set indexes or 'name' for fuzzy set names.
        :param results: the number of nearest fuzzy sets to return
        :return: a list with the nearest fuzzy sets
        """

        if self.kdtree is None:
            self.build_index()

        type = kwargs.get('type','index')
        results = kwargs.get('results', 3)

        _, ix = self.kdtree.query([data, data, data], results)

        if type == 'name':
            return [self.ordered_sets[k] for k in sorted(ix)]
        else:
            return sorted(ix)


    def plot(self, ax, rounding=0):
        """
        Plot the partitioning using the Matplotlib axis ax

        :param ax: Matplotlib axis
        """
        ax.set_title(self.name)
        ax.set_ylim([0, 1.1])
        ax.set_xlim([self.min, self.max])
        ticks = []
        x = []
        for key in self.sets.keys():
            s = self.sets[key]
            if s.type == 'common':
                self.plot_set(ax, s)
            elif s.type == 'composite':
                for ss in s.sets:
                    self.plot_set(ax, ss)
            ticks.append(str(round(s.centroid,rounding))+'\n'+s.name)
            x.append(s.centroid)
        ax.xaxis.set_ticklabels(ticks)
        ax.xaxis.set_ticks(x)

    def plot_set(self, ax, s):
        """
        Plot an isolate fuzzy set on Matplotlib axis

        :param ax: Matplotlib axis
        :param s: Fuzzy Set
        """
        if s.mf == Membership.trimf:
            ax.plot([s.parameters[0], s.parameters[1], s.parameters[2]], [0, s.alpha, 0])
        elif s.mf in (Membership.gaussmf, Membership.bellmf, Membership.sigmf):
            tmpx = np.linspace(s.lower, s.upper, 100)
            tmpy = [s.membership(kk) for kk in tmpx]
            ax.plot(tmpx, tmpy)
        elif s.mf == Membership.trapmf:
            ax.plot(s.parameters, [0, s.alpha, s.alpha, 0])
        elif s.mf == Membership.singleton:
            ax.plot([s.parameters[0],s.parameters[0]], [0, s.alpha])

    def __str__(self):
        """
        Return a string representation of the partitioner, the list of fuzzy sets and their parameters

        :return:
        """
        tmp = self.name + ":\n"
        for key in self.sets.keys():
            tmp += str(self.sets[key])+ "\n"
        return tmp

    def __len__(self):
        """
        Return the number of partitions

        :return: number of partitions
        """
        return self.partitions

    def __getitem__(self, item):
        """
        Return a fuzzy set by its order or its name.

        :param item: If item is an integer then it represents the fuzzy set index (order), if it was a string then
        it represents the fuzzy set name.
        :return: the fuzzy set
        """
        if isinstance(item, (int, np.int8, np.int16, np.int32, np.int64)): 
            if item < 0 or item >= self.partitions:
                raise ValueError("The fuzzy set index must be between 0 and {}.".format(self.partitions))
            return self.sets[self.ordered_sets[item]]
        elif isinstance(item, str):
            if item not in self.sets:
                raise ValueError("The fuzzy set with name {} does not exist.".format(item))
            return self.sets[item]
        else:
            raise ValueError("The parameter 'item' must be an integer or a string and the value informed was {} of type {}!".format(item, type(item)))


    def __iter__(self):
        """
        Iterate over the fuzzy sets, ordered by its midpoints.

        :return: An iterator over the fuzzy sets.
        """
        for key in self.ordered_sets:
            yield self.sets[key]

