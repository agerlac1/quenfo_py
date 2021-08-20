""" Script manages the training-process. The Class Model is filled with the knn classifier and the tfidf vectorizer."""

# ## Imports
from training.tfidfvectorizer import start_tfidf
from training.knnclassifier import start_knn
from classification import prepare_classifyunits
from database import session, session2
from orm_handling import models, orm
import logging
import sklearn
import dill as pickle
import yaml
from pathlib import Path
from orm_handling.models import Model, TraindataInfo, SaveModel
from typing import Union
import inspect
import os
import datetime



# ## Open Configuration-file and set variables + paths
with open(Path('config.yaml'), 'r') as yamlfile:
    cfg = yaml.load(yamlfile, Loader=yaml.FullLoader)
    models = cfg['models']
    tfidf_path = models['tfidf_path']
    knn_path = models['knn_path']
    tfidf_config = cfg['tfidf_config']
    knn_config = cfg['knn_config']
    resources = cfg['resources']
    traindata_path = resources['traindata_path']


# ## Set variables
all_features = list()
all_classes=list()
traindata_name = str()
traindata_date = str()


# ## Functions
def initialize_model() -> Model:
    """ Function to start the training/loading process of the Model. 
    a. try to load the models tfidf and knn
    b. check if models are already trained with the same configurations
    c. train again if loading fails or new configurations are set
    """
    # load traindata 
    # check if tfidfmodel is already there and if it is filled with the same trainingdata and the same parameter
        #if true: load the vectorizer and transform traindata
            # output: fitter and tfidf_train matrix -- set all_classes and all_features
        # if false: use traindata to fit the model and transform traindata
            # output: fitter tfidf_trainmatrix -- set all_classes and all_features

    # set variables global
    global all_classes
    global all_features
    global traindata_name
    global traindata_date

    # Model besteht aus vectorizer und dem knn
    model_tfidf, td_info_tfidf = load_model('model_tfidf')
    
    model_knn, td_info_knn = load_model('model_knn')

    # extract traindata name and last modification
    try:
        traindata_name = str(Path(traindata_path).name)
        traindata_date = str(datetime.datetime.fromtimestamp(os.path.getmtime(traindata_path)).replace(microsecond=0))
    except OSError:
        print("Key Information for Traindata could not be extracted. Model will be saved without Traindata Information.")
        traindata_name = traindata_date = str()

    # check if settings in configuration file for models have changed
    try:
        tfidf_bool = __check_configvalues(tfidf_config, model_tfidf)
        knn_bool = __check_configvalues(knn_config, model_knn)
    except AttributeError:
        print(f'checkup of model settings didnt work. Set both to false to start ne training.')
        tfidf_bool = False
        knn_bool = False

            
    # # check if a. models are not none b. same traindata was used c. settings are the same
    if model_tfidf is None or model_knn is None \
            or td_info_tfidf.name != traindata_name or td_info_tfidf.date != traindata_date \
                or td_info_knn.name != traindata_name or td_info_knn.date != traindata_date \
                    or tfidf_bool == False or knn_bool == False:
        
        print('one of the models tfidf or knn was not filled. Both need to be redone')
        
        # prepare data for training
        traindata = prepare_traindata()
        all_features, all_classes = __prepare_lists(traindata)

    
        # start training
        model_tfidf, tfidf_train = start_tfidf(all_features, tfidf_config)
        # hier wird knn trainiert mit tfidf_train und classes
        model_knn = start_knn(tfidf_train, all_classes)


    model = Model(model_knn=model_knn, vectorizer=model_tfidf, traindata_name = traindata_name, traindata_date = traindata_date)
    # bow traindata not needed --> hier an dieser stelle ist das knn auch schon vorhanden!

    return model

#  Help function to generate a list with all features and a list with all classes
def __prepare_lists(traindata):
    for train_obj in traindata:
        for cu in train_obj.children2:
            all_features.append(' '.join(cu.featureunits))
            all_classes.append(cu.classID)
    return all_features, all_classes

def __check_configvalues(config_values, model):
    for i in (config_values).items():
        if i in model.get_params().items():
            config_bool = True
            pass
        else:
            config_bool = False
            break
    return config_bool


def prepare_traindata():
    # ## STEP 2:
    # Load the TrainingData: TrainingData in TrainingData Class
    traindata = orm.get_traindata(session2)
    
    # fill classify_units (already there same as trainobjcontent) and genearte feature_units for Traindata
    for train_obj in traindata:
        prepare_classifyunits.generate_train_cus(train_obj)
        
    return traindata


# ## Support Functions
""" Methods to load and save models from all parts of the program."""

def save_model(model: Union[sklearn.feature_extraction.text.TfidfVectorizer or sklearn.neighbors.KNeighborsClassifier]) -> None:
    """ Method saves a passed model in path (set in config.yaml).
        
    Parameters
    ----------
    model: sklearn.feature_extraction.text.TfidfVectorizer
        The model to be saved. Type: TfidfVectorizer """
    
    model_path = None

    # Pack Model and Traindata Information in Objects to pickle dump them
    c = TraindataInfo(traindata_name, traindata_date)

    m = SaveModel(model)
    
    # set right path
    if type(model) == sklearn.feature_extraction.text.TfidfVectorizer:
        model_path = tfidf_path
    elif type(model) == sklearn.neighbors.KNeighborsClassifier:
        model_path = knn_path
    else:
        print(f'Path for {model} could not be resolved. No model was saved. Check config for path adjustment.')

    def __dumper(model_path: Path):
        with open(Path(model_path), 'wb') as fw:
            pickle.dump([m,c], fw)

    if Path(model_path).exists():
        print(f'Model {model_path} does already exist, will be overwritten.')
        __dumper(model_path)
    else:
        __dumper(model_path)

# Methods to load the tfidf-models (are used by sanity, analysis inside and outside)
def load_model(name: str) -> Union[sklearn.feature_extraction.text.TfidfVectorizer, sklearn.neighbors.KNeighborsClassifier]: 
    """ Method loads a model depending on chosen name. Path for model is set in config.yaml.
        1. __loader: loads the model and excepts Exceptions
        2. __check_model: checks the received model 
    Parameters
    ----------
    name : str
        Name of the model (model)
    
    Raises
    ------
    FileNotFoundError
        Raise Exception if model could not be loaded
    
    Returns
    -------
    model: sklearn.feature_extraction.text.TfidfVectorizer
        The saved model. Type: TfidfVectorizer """

    model = td_info = None

    def __loader(model: None, name: str):
        if name == 'model_tfidf':
            try:
                mylist = list()
                model = pickle.load(open(Path(tfidf_path), 'rb'))

                for pickle_obj in model:
                    mylist.append(pickle_obj)
                
                model = mylist[0].name
                td_info = mylist[1]

            except FileNotFoundError as err:
                model = td_info = None
        elif name == 'model_knn':
            try:
                mylist = list()
                model = pickle.load(open(Path(knn_path), 'rb'))
                for pickle_obj in model:
                    mylist.append(pickle_obj)  
                model = mylist[0].name
                td_info = mylist[1]
            except FileNotFoundError as err:
                model = td_info = None
        else:
            model = td_info = None

        return model, td_info
    model, td_info = __loader(model, name)

    def __check_model(model: Union[sklearn.feature_extraction.text.TfidfVectorizer, sklearn.neighbors.KNeighborsClassifier], name):
        try:
            # check if model is already fitted (eg from https://www.py4u.net/discuss/230863)
            if (0 < len( [k for k,v in inspect.getmembers(model) if k.endswith('_') and not k.startswith('__')])) and model is not None:
                print(f'Model {name} is loaded and returned to next processing step.')
                return model
            else:
                raise TypeError
        except sklearn.exceptions.NotFittedError and TypeError:
            print(f'Model {name} failed to be loaded or is not fitted. Check Settings in config.yaml and paths for {name}. New Trainingprocess starts.')
            return model
    model = __check_model(model, name)

    return model, td_info