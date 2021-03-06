""" Script to manage fus-processing. Contains following steps:
    First: Get Configuration Settings for fus.
    Second:
        a. Tokenization
        b. Normalization
        c. Filter Stopwords
        d. Stemming
        e. NGram-Generation """

# ## Imports
from . import convert_featureunits
from pathlib import Path
import configuration
import logger

# ## Set Variables
fus = list()

# ## Function

# FEATUREUNIT-MANAGER
def get_featureunits(cu: object) -> None:
    """ Function to manage preprocessing steps as tokenization, normalization, stopwords removal, stemming and ngrams.
    Each step receives the current featureunits of a classifyunit-object and processes them. 
    Afterwards the new fus are set as featureunits for the cu (overwriting).
    
    Parameters
    ----------
    cu: object
        classifyunit-object which contains the instantiated featureunits --> consisting of cu-paragraphs without non-alphanumerical characters """

    # Get Configuration Settings
    fus_config = configuration.config_obj.get_fus_config()
    # Tokenization --> most important step (the others are kind of optional, but better use them!)
    fus = convert_featureunits.tokenize(cu.featureunits)
    cu.set_featureunits(fus)
    # if list is not empty
    if fus:
        # Normalization
        fus = convert_featureunits.normalize(cu.featureunits, fus_config['normalize'])
        cu.set_featureunits(fus)
        # Stopwords Removal
        fus = convert_featureunits.filterSW(cu.featureunits, fus_config['filterSW'], Path(configuration.config_obj.get_stopwords_path()))
        cu.set_featureunits(fus)
        # Stemming
        fus = convert_featureunits.stem(cu.featureunits, fus_config['stem'])
        cu.set_featureunits(fus)
        # NGram Generation
        fus = convert_featureunits.gen_ngrams(cu.featureunits, fus_config['nGrams'], fus_config['continuousNGrams'])
        cu.set_featureunits(fus)
    else:
        logger.log_clf.warning(f'The current cu from parent {cu} is empty after tokenization. Prediction for this paragraph will be problematic. Continue with next cu.')