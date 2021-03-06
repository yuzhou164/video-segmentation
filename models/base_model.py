from abc import ABCMeta, abstractmethod

import keras.utils
from keras import optimizers


class BaseModel:
    __metaclass__ = ABCMeta

    @staticmethod
    def model_from_json(path, custom_objects=None):
        if custom_objects is None:
            custom_objects = {}

        with open(path, 'r') as f:
            json_string = f.read()

        return keras.models.model_from_json(json_string, custom_objects=custom_objects)

    def __init__(self, target_size, n_classes, debug_samples=0, for_training=True, from_json=None):
        """
        :param tuple target_size: (height, width)
        :param int n_classes: number of classes
        :param bool is_debug: turns off regularization
        """
        self.target_size = target_size
        self.n_classes = n_classes
        self.debug_samples = debug_samples
        self.is_debug = debug_samples > 0
        self.training_phase = for_training

        self._prepare()
        if from_json is not None:
            self._model = self.model_from_json(from_json, self.get_custom_objects())
        else:
            self._model = self._create_model()

    def _prepare(self):
        """
        Initialize any parameters for model
        :return:
        """
        pass

    def make_multi_gpu(self, n_gpu):
        from keras.utils import multi_gpu_model
        self._model = multi_gpu_model(self._model, n_gpu)

    def load_model(self, filepath, custom_objects=None, compile_model=True):
        """
        Loads model from hdf5 file with layers and weights (complete model)
        Custom layers are loaded from model, here just specify custom losses,metrics,etc

        :param str filepath:
        :param dict custom_objects: For custom metrics,losses,etc. Model will load its custom layers
        :param bool compile: True
        :return: self (for convenience)
        """

        if custom_objects is None:
            custom_objects = {}
        else:
            custom_objects = custom_objects.copy()
        custom_objects.update(self.get_custom_objects())

        self._model.load_weights(
            filepath=filepath,
            by_name=True
        )

        if compile_model:
            self.compile()

        return self

    @abstractmethod
    def _create_model(self):
        """
        Creates keras model

        :return: keras model (not compiled)
        :rtype: keras.models.Model

        """
        pass

    @property
    def name(self):
        """
        :rtype: str
        :return: name of the model (class name)
        """
        return type(self).__name__

    def summary(self):
        return self._model.summary()

    @property
    def k(self):
        """
        :rtype: keras.models.Model
        :return: keras model
        """
        return self._model

    def plot_model(self, to_file=None):
        """
        Plots mode into PNG file

        :param str to_file:
        """
        if to_file is None:
            to_file = 'plot/model_%s%s_%dx%d.png' % (self.name, "" if self.training_phase else "_TEST" , self.target_size[0], self.target_size[1])
            print("Plotting to file " + to_file)

        keras.utils.plot_model(
            self.k,
            to_file=to_file,
            show_layer_names=True,
            show_shapes=True
        )

    def save_json(self, to_file=None):
        if to_file is None:
            to_file = 'model_%s_%dx%d.json' % (self.name, self.target_size[0], self.target_size[1])
            print("Saving json to file " + to_file)

        data = self._model.to_json()

        with open(to_file, 'w') as f:
            f.write(data)

    def save_final(self, to_file, last_epoch):
        """

        :param str run_name:
        :param int last_epoch:
        :param str to_file:
        :return:
        """

        self.k.save_weights(to_file + '_%d_finished.h5' % last_epoch)

    def metrics(self):
        import metrics
        return [
            metrics.mean_iou
        ]

    @staticmethod
    def get_custom_objects():
        """dictionary of custom objects (as per keras definition)"""
        import metrics
        return {
            'mean_iou': metrics.mean_iou
        }

    lr_params = None

    def optimizer_params(self):
        if self.debug_samples == 120:
            return {'lr': 0.0001, 'decay': 0.05}
        else:
            return {'lr': 0.001, 'decay': 0.05}

    def _optimizer_params(self):
        if self.lr_params is not None:
            return self.lr_params
        else:
            return self.optimizer_params()

    def params(self):
        return {
            'optimizer': {
                'name': type(self.optimizer()).__name__,
                'lr': self._optimizer_params()['lr'],
                'decay': self._optimizer_params()['decay'],
            }
        }

    def optimizer(self):
        params = self._optimizer_params()
        return optimizers.Adam(lr=params['lr'], decay=params['decay'])

    def loss_weights(self):
        return None

    def compile(self, lr=None, lr_decay=0.):
        if lr is not None:
            self.lr_params = {'lr': lr, 'decay': lr_decay}

        print("-- Optimizer: " + type(self.optimizer()).__name__)
        print("---- Params: ", self._optimizer_params())
        print("---- For Training: ", self.training_phase)

        self._model.compile(
            loss=keras.losses.categorical_crossentropy,
            optimizer=self.optimizer(),
            metrics=self.metrics(),
            loss_weights=self.loss_weights()
        )
