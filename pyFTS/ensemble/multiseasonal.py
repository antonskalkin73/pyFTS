#!/usr/bin/python
# -*- coding: utf8 -*-

import numpy as np
import pandas as pd
import math
from operator import itemgetter
from pyFTS.common import FLR, FuzzySet, SortedCollection
from pyFTS import fts, chen, cheng, hofts, hwang, ismailefendi, sadaei, song, yu, sfts
from pyFTS.benchmarks import arima, quantreg
from pyFTS.common import Transformations, Util as cUtil
import scipy.stats as st
from pyFTS.ensemble import ensemble
from pyFTS.models import msfts, cmsfts
from pyFTS.probabilistic import ProbabilityDistribution, kde
from copy import deepcopy
from joblib import Parallel, delayed
import multiprocessing


def train_individual_model(partitioner, train_data, indexer):
    pttr = str(partitioner.__module__).split('.')[-1]
    diff = "_diff" if partitioner.transformation is not None else ""
    _key = "msfts_" + pttr + str(partitioner.partitions) + diff + "_" + indexer.name

    print(_key)

    model = cmsfts.ContextualMultiSeasonalFTS(_key, indexer=indexer)
    model.appendTransformation(partitioner.transformation)
    model.train(train_data, partitioner.sets, order=1)

    cUtil.persist_obj(model, "models/"+_key+".pkl")

    return model


class SeasonalEnsembleFTS(ensemble.EnsembleFTS):
    def __init__(self, name, **kwargs):
        super(SeasonalEnsembleFTS, self).__init__(name="Seasonal Ensemble FTS", **kwargs)
        self.min_order = 1
        self.indexers = []
        self.partitioners = []
        self.is_multivariate = True
        self.has_seasonality = True
        self.has_probability_forecasting = True

    def update_uod(self, data):
        self.original_max = max(self.indexer.get_data(data))
        self.original_min = min(self.indexer.get_data(data))

    def train(self, data, sets, order=1, parameters=None):
        self.original_max = max(self.indexer.get_data(data))
        self.original_min = min(self.indexer.get_data(data))

        num_cores = multiprocessing.cpu_count()

        pool = {}
        count = 0
        for ix in self.indexers:
            for pt in self.partitioners:
                pool[count] = {'ix': ix, 'pt': pt}
                count += 1

        results = Parallel(n_jobs=num_cores)(
            delayed(train_individual_model)(deepcopy(pool[m]['pt']), data, deepcopy(pool[m]['ix']))
            for m in pool.keys())

        for tmp in results:
            self.appendModel(tmp)

        cUtil.persist_obj(self, "models/"+self.name+".pkl")

    def forecastDistribution(self, data, **kwargs):

        ret = []

        smooth = kwargs.get("smooth", "KDE")
        alpha = kwargs.get("alpha", None)

        for k in data.index:

            tmp = self.get_models_forecasts(data.ix[k])

            if alpha is None:
                tmp = np.ravel(tmp).tolist()
            else:
                tmp = self.get_distribution_interquantile( np.ravel(tmp).tolist(), alpha)

            name = str(self.indexer.get_index(data.ix[k]))

            dist = ProbabilityDistribution.ProbabilityDistribution(smooth,
                                                                   uod=[self.original_min, self.original_max],
                                                                   data=tmp, name=name, **kwargs)

            ret.append(dist)

        return ret