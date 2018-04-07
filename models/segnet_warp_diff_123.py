import keras
from keras import Input, Model, optimizers
from keras.layers import Convolution2D, BatchNormalization, Activation, MaxPooling2D, UpSampling2D, Reshape, Lambda, \
    Add, SpatialDropout2D

from segnet_warp_diff import SegNetWarpDiff


class SegNetWarpDiff123(SegNetWarpDiff):
    def _create_model(self):
        img_old = Input(shape=self.target_size + (3,), name='data_old')
        img_new = Input(shape=self.target_size + (3,), name='data_new')
        flo = Input(shape=self.target_size + (2,), name='data_flow')
        diff = Input(shape=self.target_size + (3,), name='data_diff')

        all_inputs = [img_old, img_new, flo, diff]

        # encoder
        transformed_flow = self.netwarp_module(img_old, img_new, flo, diff)

        flow1 = MaxPooling2D(pool_size=self._pool_size, name='flow_down_1')(transformed_flow)
        flow2 = MaxPooling2D(pool_size=self._pool_size, name='flow_down_2')(flow1)
        flow3 = MaxPooling2D(pool_size=self._pool_size, name='flow_down_3')(flow2)

        # new branch
        new_branch = self._block(img_new, self._filter_size, self._kernel_size, self._pool_size)
        old_branch = self._block(img_old, self._filter_size, self._kernel_size, self._pool_size)

        warped1 = Lambda(self.warp, name="warp1")([old_branch, flow1])
        warped1 = self._block(warped1, 128, self._kernel_size, self._pool_size)
        warped1 = self._block(warped1, 256, self._kernel_size, self._pool_size)
        warped1 = self._block(warped1, 512, self._kernel_size, pool_size=None)

        new_branch2 = self._block(new_branch, 128, self._kernel_size, self._pool_size)
        old_branch2 = self._block(old_branch, 128, self._kernel_size, self._pool_size)

        warped2 = Lambda(self.warp, name="warp2")([old_branch2, flow2])
        warped2 = self._block(warped2, 256, self._kernel_size, self._pool_size)
        warped2 = self._block(warped2, 512, self._kernel_size, pool_size=None)

        new_branch3 = self._block(new_branch2, 256, self._kernel_size, self._pool_size)
        old_branch3 = self._block(old_branch2, 256, self._kernel_size, self._pool_size)

        new_branch4 = self._block(new_branch3, 512, self._kernel_size, pool_size=None)
        old_branch4 = self._block(old_branch3, 512, self._kernel_size, pool_size=None)

        warped3 = Lambda(self.warp, name="warp3")([old_branch4, flow3])
        out = Add()([warped1, warped2, warped3, new_branch4])

        if not self.is_debug:
            out = SpatialDropout2D(0.3)(out)

        # decoder
        out = Convolution2D(512, self._kernel_size, padding='same')(out)
        out = BatchNormalization()(out)

        out = UpSampling2D(size=self._pool_size)(out)
        out = Convolution2D(256, self._kernel_size, padding='same')(out)
        out = BatchNormalization()(out)

        out = UpSampling2D(size=self._pool_size)(out)
        out = Convolution2D(128, self._kernel_size, padding='same')(out)
        out = BatchNormalization()(out)

        out = UpSampling2D(size=self._pool_size)(out)
        out = Convolution2D(self._filter_size, self._kernel_size, padding='same')(out)
        out = BatchNormalization()(out)

        out = Convolution2D(self.n_classes, (1, 1), padding='same')(out)

        out = Reshape((-1, self.n_classes))(out)
        out = Activation('softmax')(out)

        model = Model(inputs=all_inputs, outputs=[out])

        return model

    def _compile_release(self, m_metrics):
        self._model.compile(
            loss=keras.losses.categorical_crossentropy,
            optimizer=optimizers.Adam(decay=0.00001),
            metrics=m_metrics
        )


if __name__ == '__main__':
    target_size = (288, 480)
    model = SegNetWarpDiff(target_size, 34)

    print(model.summary())
    keras.utils.plot_model(model.k, 'segnet_warp_diff.png', show_shapes=True, show_layer_names=True)