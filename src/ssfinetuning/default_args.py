from transformers import TrainingArguments
import numpy as np
from .dataset_utils import extract_keys
from transformers import Trainer
from transformers import AutoTokenizer
import warnings


def get_default_cm():
    """
    Default compute metric function.
    """
    from datasets import load_metric
    metric = load_metric('glue', "cola")

    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)
        return metric.compute(predictions=predictions, references=labels)

    return compute_metrics


def encode(dataset, model_name='albert-base-v2', text_column_name='sentence'):
    """
    Function for encoding the dataset using tokenizer

    Args:

    dataset (:obj:`~datasets.DatasetDict` ): Dataset dictionary containing labeled
    and unlabeled data.

    model_name (:obj:`str` or :obj:`os.PathLike`): "pretrained_model_name_or_path"
    in ~transformers.PreTrainedModel, please refer to its documentation for further
    information.

    (i) In this case of a string, the `model id` of a pretrained model
    hosted inside a model repo on huggingface.co.

    (ii) It could also be address of saved pretrained model.

    text_column_name (:obj:`str`): column name for where the text is.

    Return:

    encoded_dataset (:obj:`~datasets.DatasetDict` ): containing columns now
    which are required by the forward function.

    tokenizer (:obj:`~transformers.PreTokenizer` ):

    """

    try:
      tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    except:
      tokenizer = AutoTokenizer.from_pretrained('cardiffnlp/twitter-xlm-roberta-base-sentiment',model_max_length=512 )

    def preprocess_function(examples):
        return tokenizer(examples[text_column_name], truncation=True)

    encoded_dataset = dataset.map(preprocess_function, batched=True)

    return encoded_dataset, tokenizer


class DefaultArgs:

    def __init__(self):

        # Default keyword arguments for transformers.TrainingArguments for
        # supervised and semisupervised models. Set_default_args changes
        # this dictionary depending what setup of args or args_sup in the
        # train_with_ssl keyword arguments.

        self.kwargs_args_sup = {
            'output_dir': "glue",
            'evaluation_strategy': "epoch",
            'learning_rate': 2e-5,
            'per_device_train_batch_size': 16,
            'per_device_eval_batch_size': 16,
            'num_train_epochs': 10,
            'weight_decay': 0.01,
            'metric_for_best_model': "matthews_correlation",
            'load_best_model_at_end': True,
            'disable_tqdm': True,
            'no_cuda': True}

        self.kwargs_args = self.kwargs_args_sup.copy()
        self.kwargs_args['save_steps'] = np.inf

    def set_default_args(self, dataset, model_name, kwargs):
        """
        Function for setting the default arguments if these keywords are not
        provided in kwargs of train_with_ssl. Updates the kwargs to be used
        transformers.Trainer.
        Args:
        dataset (:obj:`~datasets.DatasetDict` ): Dataset dictionary containing
        labeled and unlabelled data.
        model_name (:obj:`str` or :obj:`os.PathLike`):
        "pretrained_model_name_or_path" in ~transformers.PreTrainedModel,
        please refer to its documentation for further information.
        (i) In this case of a string, the `model id` of a pretrained model
        hosted inside a model repo on huggingface.co.
        (ii) It could also be address of saved pretrained model.
        kwargs (:obj:`dict`): keyword arguments to be used by
        transformers.Trainer.
        """

        kwargs_trn = extract_keys(Trainer, kwargs)

        if 'compute_metrics' not in kwargs_trn.keys():
            kwargs_trn['compute_metrics'] = get_default_cm()

        if 'tokenizer' not in kwargs_trn.keys():
            text_column_name = kwargs.pop('text_column_name', 'sentence')
            encoded_dataset, tokenizer = encode(dataset, model_name, text_column_name)
            kwargs_trn['tokenizer'] = tokenizer

        else:
            warnings.warn('tokenizer found. If using tokenizer, please use the encoded dataset. Like done using'
                          '~set_default_args.encode()')

        if 'args_ta_sup' in kwargs.keys():

            if isinstance(kwargs['args_ta_sup'], dict):
                self.kwargs_args_sup.update(kwargs['args_ta_sup'])
                del kwargs['args_ta_sup']

        if 'args_ta' in kwargs.keys():

            if isinstance(kwargs['args_ta'], dict):
                self.kwargs_args.update(kwargs['args_ta'])
                del kwargs['args_ta']

        kwargs.update(kwargs_trn)
        return encoded_dataset, self.kwargs_args

    def get_default_ta_sup(self, logging_dir=''):
        """
        Return the TrainingArguments with the logging_dir setup for supervised model.
        """
        self.kwargs_args_sup['logging_dir'] = logging_dir
        return TrainingArguments(**self.kwargs_args_sup)

    def get_default_ta(self, logging_dir=''):
        """
        Return the TrainingArguments with the logging_dir setup for semisupervised model.
        """
        self.kwargs_args['logging_dir'] = logging_dir
        return TrainingArguments(**self.kwargs_args)
