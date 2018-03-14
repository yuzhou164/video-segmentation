import os
import random
import re

import cityscapes_labels
import config
import cv2

from base_generator import BaseDataGenerator


class CityscapesGenerator(BaseDataGenerator):
    def __init__(self, dataset_path, debug_samples=0, how_many_prev=0):
        dataset_path = os.path.join(dataset_path, 'cityscapes/')
        self._file_pattern = re.compile("(?P<city>[^_]*)_(?:[^_]+)_(?P<frame>[^_]+)_gtFine_color\.png")
        self._how_many_prev = how_many_prev
        super(CityscapesGenerator, self).__init__(dataset_path, debug_samples)

    _city_labels = [lab.color for lab in cityscapes_labels.labels]

    _config = {
        'labels': _city_labels,
        'n_classes': len(_city_labels),
        "std": (0.1829540508368939, 0.18656561047509476, 0.18447508988480435),
        "mean": (0.29010095242892997, 0.32808144844279574, 0.28696394422942517)
    }

    @property
    def name(self):
        return 'cityscapes'

    @property
    def config(self):
        return self._config

    def _fill_split(self, which_set):
        img_path = os.path.join(self.dataset_path, 'leftImg8bit', which_set, '')
        lab_path = os.path.join(self.dataset_path, 'gtFine', which_set, '')

        # Get file names for this set
        filenames = []
        for root, dirs, files in os.walk(lab_path):
            for gt_name in files:
                if gt_name.startswith('._') or not (gt_name.endswith('_color.png')):
                    continue

                match = self._file_pattern.match(gt_name)
                if match is None:
                    print("skipping path %s" % path)
                    continue

                match_dict = match.groupdict()
                frame_i = int(match_dict['frame'])

                img_name = os.path.join(img_path, match_dict['city'], gt_name)
                if self._how_many_prev == 0:
                    i_batch = img_name.replace("gtFine_color", "leftImg8bit")
                else:
                    i_batch = []
                    for i in range(frame_i - self._how_many_prev, frame_i):
                        frame_str = str(i).zfill(6)
                        name_i = img_name \
                            .replace(match_dict['frame'], frame_str) \
                            .replace("gtFine_color", "leftImg8bit")
                        i_batch.append(name_i)
                    i_batch.append(img_name.replace("gtFine_color", "leftImg8bit"))

                filenames.append((i_batch, os.path.join(root, gt_name)))

        if not (self._debug_samples):
            print("Cityscapes: shuffling dataset")
            random.shuffle(filenames)

        print('Cityscapes: ' + which_set + ' ' + str(len(filenames)) + ' files')

        self._data[which_set] = filenames

        # # Get file names for this set
        # filenames = []
        # for root, dirs, files in os.walk(img_path):
        #     for name in files:
        #         file = os.path.join(root[-root[::-1].index('/'):], name)
        #         img_file = os.path.join(img_path, file)
        #         lab_file = os.path.join(lab_path, file.replace("leftImg8bit", "gtFine_color"))
        #         filenames.append((img_file, lab_file))
        #
        # if not(self._debug_samples):
        #     print("Cityscapes: shuffling dataset")
        #     random.shuffle(filenames)
        #
        # print('Cityscapes: ' + which_set + ' ' + str(len(filenames)) + ' files')
        #
        # self._data[which_set] = filenames


if __name__ == '__main__':
    if __package__ is None:
        import sys
        from os import path

        sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
    else:
        __package__ = ''

    datagen = CityscapesGenerator(config.data_path())

    batch_size = 3
    # target_size = 288, 480
    target_size = 256, 512
    # target_size = 1024, 2048  # orig size

    for imgBatch, labelBatch in datagen.flow('val', batch_size, target_size):
        print(len(imgBatch))

        img = imgBatch[0]
        label = labelBatch[0]

        print(img.shape, label.shape)

        colored_class_image = datagen.one_hot_to_bgr(label, target_size, datagen.n_classes, datagen.labels)

        cv2.imshow("normalized", img)
        cv2.imshow("gt", colored_class_image)
        cv2.waitKey()
