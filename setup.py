import setuptools

setuptools.setup(
    name='pyFTS',
    install_requires=[
          'matplotlib',
          'numpy',
          'pandas'],
    packages=['pyFTS', 'pyFTS.benchmarks', 'pyFTS.common', 'pyFTS.common.transformations', 'pyFTS.data', 
              'pyFTS.models.ensemble', 'pyFTS.models', 'pyFTS.models.seasonal', 'pyFTS.partitioners', 
              'pyFTS.probabilistic', 'pyFTS.tests', 'pyFTS.models.nonstationary', 'pyFTS.models.multivariate',
              'pyFTS.models.incremental', 'pyFTS.hyperparam', 'pyFTS.distributed', 'pyFTS.fcm'],	
    version='1.7',
    description='Fuzzy Time Series for Python',
    long_description='Fuzzy Time Series for Python',
    long_description_content_type="text/markdown",
    author='Petronio Candido L. e Silva',
    author_email='petronio.candido@gmail.com',
    url='https://pyfts.github.io/pyFTS/',
    download_url='https://github.com/PYFTS/pyFTS/archive/pkg1.7.tar.gz',
    keywords=['forecasting', 'fuzzy time series', 'fuzzy', 'time series forecasting'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Topic :: Scientific/Engineering',
        'Development Status :: 5 - Production/Stable'
    
    ]
)
