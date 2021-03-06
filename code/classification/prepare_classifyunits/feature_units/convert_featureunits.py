"""Script contains several functions to modify featureunits."""

# ## Imports
import logger
from pathlib import Path
import re
from contextlib import suppress
from nltk.stem.snowball import GermanStemmer
from nltk import ngrams
from nltk.stem.cistem import Cistem
from yaml.reader import ReaderError

# ## Set Variables
sw_list = list()

# ## Functions

# Remove all non-alphanumerical characters
def replace(para: str) -> str:
    """ The replace function replaces all non-alphanumerical characters with a whitespace via regex

    Parameters
    ----------
    para: str
        para variable contains the paragraph of a jobad as string
    
    Returns
    -------
    para: str
        returns para variable without non-alphanumerical characters"""
    try:
        # Regex to replace all non-alphanumerical chars with whitespaces
        para = re.sub('\W+', ' ', para)
        #para = re.sub('\W+|[_]+', ' ', para)
    except Exception:
        para = para
    return para


# Tokenization
def tokenize(fus: str) -> list:
    """ Function to tokenize the given string fus

    Parameters
    ----------
    fus: str
        contains the current state of fus (still as string)
    
    Returns
    -------
    fus: list
        returns fus as list with token """
    try:
        # Regex to tokenize the given string
        WORD = re.compile(r'\w+')
        fus = WORD.findall(fus)
    except Exception:
        try:
            # different approach 
            fus = fus.split()
        except Exception:
            fus = []
    return fus


# Normalization
def normalize(fus: list, normalize: bool) -> list:
    """ The normalization function contains 3 steps:
        a. lower case
        b. replace token with beginning and ending digits as characters with NUM
        c. append only token with more than one character to output list

    Parameters
    ----------
    fus: list
        the list contains the featureunits of a paragraph aka token
    normalize: boolean
        bool value from config to determine if normalization step is executed 
        
    Returns
    --------
    norm_fus: list
        list with normalized token, is used as fus for a paragraph """

    # normalized fus are stored in new list
    norm_fus = list()
    # Check if normalize is set to true and use the following normalization step
    if normalize:
        try:
            # for token in token_list
            for fu in fus:
                # Lower Case
                fu = fu.lower()
                # if token starts and ends with a digit-character --> set token to NUM because it won't be processable
                if fu[0].isdigit() and fu[-1].isdigit():
                    fu = 'NUM'
                # filter 
                if len(fu) > 1:
                    norm_fus.append(fu)
            return norm_fus
        except Exception as e:
            logger.log_clf.warning(f'While Normalization error {e} raised. Continue without normalization step for current paragraph.')
    else:
        return fus
    


# Stopwords Removal
def filterSW(fus: list, filterSW: bool, sw_path: Path) -> list:
    """ Function filterSW compares the given token list with the stopwords in the lookup file and removes them.

    Parameters
    ----------
    fus: list
        the list contains the featureunits of a paragraph as token
    filterSW: boolean
        bool value from config to determine if stopwords removal step is executed 
    sw_path: Path
        Pathlib-object contains the Path (stored in config) to the stopwords lookup file
        
    Returns
    --------
    fus: list
        list with token after stopwords are removed """

    # fill stopwords list from file once
    __check_once(sw_path)
    # remove all stopwords from fus
    if filterSW:
        try:
            for sw in sw_list:
                if sw != "ERROR":
                    # Normally if the stopword sw is found in fus it skips to the next sw. But it is possible that a sw
                    # occurs multiple times in fus: with suppress(ValueError) is another way of handling try and except
                    # statements.
                    with suppress(ValueError):
                        # remove also duplicated sw in fus --> while True
                        while True:
                            fus.remove(sw.lower())
                else:
                    pass
        except Exception as e:
            logger.log_clf.warning(f'While Stopword-removal error {e} raised. Continue without sw-removal step for current paragraph.')
    return fus


def __check_once(sw_path):
    global sw_list
    if not sw_list:
        try:
            with open(sw_path, 'r') as sw_file:
                sw_list = [sw.strip() for sw in sw_file.readlines()]
        except (FileNotFoundError, ReaderError) as error:
            logger.log_clf.warning(f'Error {error} is raised. Continue without stopwords removal.')
            sw_list = "ERROR"
    else:
        pass


# Stemming
def stem(fus: list, stem: bool) -> list:
    """ Function is used to stem the given fus as list of token. Currently the NLTK Snowball Stemmer is used.
    Other possibility is the NLTK Cistem Stemmer (currently commented out)

    Parameters
    ----------
    fus: list
        the list contains the featureunits of a paragraph as token
    stem: boolean
        bool value from config to determine if stemming step is executed 
   
    Returns
    --------
    stmmed_fus: list
        list with  stemmed token """

    # Variables
    stemmed_fus = list()
    # Check config-setting
    if stem:
        try:
            # Snowball Stemmer from NLTK
            stemmer = GermanStemmer()
            # Stem each token
            for token in fus:
                stemmed_fus.append(stemmer.stem(token))

            """ # NLTK Cistem Stemmer --> other possibility for stemming --> test in classification
            stemmer = Cistem()
            for token in fus:
                stemmed_fus.append(stemmer.segment(token)[0]) """

            # remove empty strings and strings <= 1
            stemmed_fus = list(filter(lambda n: 1 <= len(n), stemmed_fus))

            return stemmed_fus
        except Exception as e:
            logger.log_clf.warning(f'While Stemming error {e} raised. Continue without stemming step for current paragraph.')
    else:
        return fus


# NGram Generation
def gen_ngrams(fus: list, ngram_numbers: dict, cngrams: bool) -> list:
    """ Function is used to generate ngrams from given token list (fus). 1. ngram_numbers: With the var ngram_numbers
    to numbers are passed for two different ngram-cycles: e.g. {3, 4} means, that at first 3-grams are generated from
    the fus-list and added to an output list. Then 4-grams are generated from the same fus-list and those are added
    to the output-list too. So in the end the output contains 3-grams and 4-grams of the passed fus-list. ({3} or {2,4,5} also possible) 2. cngrams:
    the bool determines if the ngrams are genereated continuously across token borders (true) or only for each
    isolated token (false): e.g. pasta basta (in the example only 3-grams are shown, but normally also 4-grams are
    added) --> true: (p,a,s), (a,s,t), (s,t,a), (t,a,' '), (a,' ',b), (' ',b,a), (b,a,s), (a,s,t), (s,t,a) (including
    whitespaces) --> false: (p,a,s), (a,s,t), (s,t,a), (b,a,s), (a,s,t), (s,t,a) (only each token is separated)

    Parameters 
    ---------- 
    fus: list the list contains the featureunits as token ngram_numbers: dict dictionary
    contains the config-setting for what length of ngrams are generated --> passed numbers determine two different
    cycles. cngrams: boolean bool value from config to determine if ngrams or continuous ngrams (across tokenborders)
    are generated
   
    Returns
    --------
    fus: list
        list with ngrams generated from fus-token """
    
    # Check if the config-settings are valid numbers
    if all(isinstance(x, int) for x in ngram_numbers):
        # False == Non-Continuous: Ngrams are generated for each token isolated
        if not cngrams:
            try: 
                ngrams_complete = list()
                # e.g. first 3-grams and then 4-grams are generated ({3,4})
                for ngram_nr in ngram_numbers:
                    for fu in fus:
                        ngrams_store = list()
                        for s in ngrams(fu, n=ngram_nr):
                            ngrams_store.append("".join(s))
                        # add 3-grams to list (extend) and then add 4-grams to list
                        ngrams_complete.extend(ngrams_store)
                fus = ngrams_complete
            except Exception as e:
                logger.log_clf.warning(f'While ngram-generation error {e} raised. Continue without ngrams step for current paragraph.')
        else:
            try:
                # continuous == True --> across token borders
                onestring = " ".join(fus)       # join token to one string and keep whitespaces
                ngrams_store = list()
                # e.g. first 3-grams and then 4-grams are generated ({3,4})
                for ngram_nr in ngram_numbers:
                    for s in ngrams(onestring, n=ngram_nr):
                        ngrams_store.append("".join(s))
                fus = ngrams_store
            except Exception as e:
                logger.log_clf.warning(f'While cngram-generation error {e} raised. Continue without cngrams step for current paragraph.')
    return fus