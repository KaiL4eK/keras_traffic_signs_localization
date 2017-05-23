from keras.models import Sequential
from keras.losses import binary_crossentropy, mean_squared_error, hinge
from keras.layers import Input, concatenate, Conv2D, MaxPooling2D, UpSampling2D, ZeroPadding2D, Dropout, Deconv2D, Flatten, Dense
from keras.optimizers import Adam
from keras.callbacks import ModelCheckpoint
from keras import backend as K
from keras.utils.layer_utils import print_summary
from keras.utils.vis_utils import plot_model
import numpy as np
import cv2

import tensorflow as tf

K.set_image_data_format('channels_last')  # TF dimension ordering in this code

nn_img_side = 144

# Output is resized, BGR, mean subtracted, [0, 1.] scaled by values
def preprocess_img(img):
	img = cv2.resize(img, (nn_img_side, nn_img_side), interpolation = cv2.INTER_LINEAR)
	img = img.astype('float32', copy=False)
	img[:,:,0] -= 103.939
	img[:,:,1] -= 116.779
	img[:,:,2] -= 123.68
	img /= 255.
	return img

def intersect_over_union_bbox(y_true, y_pred):

	y_true_f = y_true
	y_pred_f = y_pred

	pred_ul_x = y_pred_f[:, 0]
	pred_ul_y = y_pred_f[:, 1]
	pred_lr_x = y_pred_f[:, 0] + y_pred_f[:, 2]
	pred_lr_y = y_pred_f[:, 1] + y_pred_f[:, 3]

	true_ul_x = y_true_f[:, 0]
	true_ul_y = y_true_f[:, 1]
	true_lr_x = y_true_f[:, 0] + y_true_f[:, 2]
	true_lr_y = y_true_f[:, 1] + y_true_f[:, 3]

	true_width  = y_true_f[:, 2]
	true_height = y_true_f[:, 3]

	pred_width  = y_pred_f[:, 2]
	pred_height = y_pred_f[:, 3]

	pred_lr_x = K.clip(pred_lr_x, 0, 1)
	pred_lr_y = K.clip(pred_lr_y, 0, 1)

	# pred1 = K.less_equal( pred_lr_x, pred_ul_x )
	# pred2 = K.less_equal( pred_lr_y, pred_ul_y )
	# sess = K.get_session()
	# if sess.run(pred1) or sess.run(pred2):
		# return K.variable(0);

	xA = K.maximum(true_ul_x, pred_ul_x)	# Left
	yA = K.maximum(true_ul_y, pred_ul_y)	# Up
	xB = K.minimum(true_lr_x, pred_lr_x)	# Right
	yB = K.minimum(true_lr_y, pred_lr_y)	# Down

	boxAArea = pred_width * pred_height
	boxBArea = true_width * true_height

	xNotIntersect = tf.logical_or(K.greater(true_ul_x, pred_lr_x), 
							   K.greater(pred_ul_x, true_lr_x))

	yNotIntersect = tf.logical_or(K.greater(true_ul_y, pred_lr_y), 
							   K.greater(pred_ul_y, true_lr_y))

	notIntersect = tf.logical_or(xNotIntersect, yNotIntersect)

	# x_inter_1 = true_ul_x - pred_lr_x
	# x_inter_1_sign = K.sign(x_inter_1)
	# # x_inter_1_val = K.clip(K.abs(true_ul_x - pred_lr_x), 10e-9, 1)

	# x_inter_2 = pred_ul_x - true_lr_x
	# x_inter_2_sign = K.sign(x_inter_2)
	# # x_inter_2_val = K.clip(K.abs(pred_ul_x - true_lr_x), 10e-9, 1)

	# xIntersect =  x_inter_1 * x_inter_2
	# # xIntersect = K.clip( xIntersect * 10e9, 0, 1 )

	# y_inter_1 = true_ul_y - pred_lr_y
	# y_inter_1_sign = K.sign(y_inter_1)
	# # y_inter_1_val = K.clip(K.abs(true_ul_y - pred_lr_y), 10e-9, 1)

	# y_inter_2 = pred_ul_y - true_lr_y
	# y_inter_2_sign = K.sign(y_inter_2)
	# # y_inter_2_val = K.clip(K.abs(pred_ul_y - true_lr_y), 10e-9, 1)

	# yIntersect = y_inter_1 * y_inter_2
	# # yIntersect = K.clip( yIntersect * 10e9, 0, 1 )

	# yIntersect = K.switch(K.greater_equal(yIntersect, 0), 1, 0)
	# xIntersect = K.switch(K.greater_equal(xIntersect, 0), 1, 0)

	intersection = tf.multiply((xB - xA), (yB - yA))
	res = tf.where(notIntersect, (K.abs(intersection) * -1) / (boxAArea + boxBArea),
								 intersection / (boxAArea + boxBArea - intersection));
	return res

def iou_loss(y_true, y_pred):
	return (1-intersect_over_union_bbox(y_true, y_pred)) * 100

def check_shape_metrics(y_true, y_pred):
	return K.shape(y_true)[0]


def regression_model():
	model = Sequential()

	model.add(Conv2D(32,(3,3),activation='relu',padding='same', input_shape=(nn_img_side, nn_img_side, 3)))
	model.add(MaxPooling2D(pool_size=(2, 2)))
	model.add(Dropout(0.25))

	model.add(Conv2D(64,(3,3),activation='relu',padding='same'))
	model.add(MaxPooling2D(pool_size=(2, 2)))
	model.add(Dropout(0.25))

	# model.add(Conv2D(64,(3,3),activation='relu',padding='same'))
	# model.add(Conv2D(128,(3,3),activation='relu',padding='same'))
	model.add(Conv2D(128,(3,3),activation='relu',padding='same'))
	model.add(MaxPooling2D(pool_size=(2, 2)))
	model.add(Dropout(0.25))

	# model.add(Conv2D(256,(3,3),activation='relu',padding='same'))
	# model.add(Conv2D(256,(3,3),activation='relu',padding='same'))
	# model.add(MaxPooling2D(pool_size=(2, 2)))
	# model.add(Dropout(0.25))

	# model.add(Conv2D(256,(3,3),activation='relu',padding='same'))
	model.add(Conv2D(256,(3,3),activation='relu',padding='same'))
	model.add(MaxPooling2D(pool_size=(2, 2)))
	# model.add(Dropout(0.25))

	# model.add(Conv2D(256,(3,3),activation='relu',padding='same'))
	model.add(Conv2D(512,(3,3),activation='relu',padding='same'))
	model.add(MaxPooling2D(pool_size=(2, 2)))
	model.add(Dropout(0.25))

	model.add(Flatten())
	# model.add(Dense(512,activation='relu'))
	# model.add(Dropout(0.5))
	model.add(Dense(1024,activation='relu'))
	model.add(Dropout(0.5))
	model.add(Dense(4,activation='sigmoid'))

	print_summary(model)
	model.compile(optimizer=Adam(lr=1e-4), loss=iou_loss, metrics=[])

	return model
