"""
First Order Traditional Fuzzy Time Series method by Song & Chissom (1993)

Q. Song and B. S. Chissom, “Fuzzy time series and its models,” Fuzzy Sets Syst., vol. 54, no. 3, pp. 269–277, 1993.
"""

import numpy as np
from pyFTS.common import FuzzySet, FLR, fts


class ConventionalFTS(fts.FTS):
    """Traditional Fuzzy Time Series"""
    def __init__(self, name, **kwargs):
        super(ConventionalFTS, self).__init__(1, "FTS " + name, **kwargs)
        self.name = "Traditional FTS"
        self.detail = "Song & Chissom"
        if self.sets is not None and self.partitioner is not None:
            self.sets = self.partitioner.sets

        self.R = None

        if self.sets is not None:
            self.R = np.zeros((len(self.sets),len(self.sets)))


    def flr_membership_matrix(self, flr):
        lm = [flr.LHS.membership(k.centroid) for k in self.sets]
        rm = [flr.RHS.membership(k.centroid) for k in self.sets]

        r = np.zeros((len(self.sets), len(self.sets)))
        for k in range(0,len(self.sets)):
            for l in range(0, len(self.sets)):
                r[k][l] = min(lm[k],rm[l])

        return r

    def operation_matrix(self, flrs):
        if self.R is None:
            self.R = np.zeros((len(self.sets), len(self.sets)))
        for k in flrs:
            mm = self.flr_membership_matrix(k)
            for k in range(0, len(self.sets)):
                for l in range(0, len(self.sets)):
                    self.R[k][l] = max(r[k][l], mm[k][l])


    def train(self, data, **kwargs):
        if kwargs.get('sets', None) is not None:
            self.sets = kwargs.get('sets', None)
        ndata = self.apply_transformations(data)
        tmpdata = FuzzySet.fuzzyfy_series_old(ndata, self.sets)
        flrs = FLR.generate_non_recurrent_flrs(tmpdata)
        self.operation_matrix(flrs)

    def forecast(self, data, **kwargs):

        ndata = np.array(self.apply_transformations(data))

        l = len(ndata)
        npart = len(self.sets)

        ret = []

        for k in np.arange(0, l):
            mv = FuzzySet.fuzzyfy_instance(ndata[k], self.sets)

            r = [max([ min(self.R[i][j], mv[j]) for j in np.arange(0,npart) ]) for i in np.arange(0,npart)]

            fs = np.ravel(np.argwhere(r == max(r)))

            if len(fs) == 1:
                ret.append(self.sets[fs[0]].centroid)
            else:
                mp = [self.sets[s].centroid for s in fs]

                ret.append( sum(mp)/len(mp))

        ret = self.apply_inverse_transformations(ret, params=[data])

        return ret

    def __str__(self):
        tmp = self.name + ":\n"
        return tmp + str(self.R)
