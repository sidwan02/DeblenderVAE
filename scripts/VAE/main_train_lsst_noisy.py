# Import necessary librairies
import numpy as np
import matplotlib.pyplot as plt
import tensorflow.keras
import sys
import os
import logging
import galsim
import random
import cmath as cm
import math
from tensorflow.keras import backend as K
from tensorflow.keras import metrics
from tensorflow.keras.models import Model, Sequential
from scipy.stats import norm
from tensorflow.keras import backend as K
from tensorflow.keras import metrics
from tensorflow.keras.layers import Conv2D, Input, Dense, Dropout, MaxPool2D, Flatten,  Reshape, UpSampling2D, Cropping2D, Conv2DTranspose, PReLU, Concatenate, Lambda, BatchNormalization, concatenate
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras import metrics
from tensorflow.keras.callbacks import Callback, ReduceLROnPlateau, TerminateOnNaN, ModelCheckpoint
import tensorflow as tf
import tensorflow_probability as tfp

from generator_vae import BatchGenerator

sys.path.insert(0,'../tools_for_VAE/')
from tools_for_VAE import model, vae_functions, utils, generator
from tools_for_VAE.callbacks import changeAlpha

######## Set some parameters
batch_size = 100
latent_dim = 32
epochs = 10000
bands = [4,5,6,7,8,9]

images_dir = '/sps/lsst/users/barcelin/data/single_galaxies/validation/'
path_output = '/sps/lsst/users/barcelin/weights/LSST/VAE/noisy/v15/mse/'

######## Import data for callback (Only if VAEHistory is used)
x_val = np.load(os.path.join(images_dir, 'galaxies_isolated_20191022_0_images.npy'))[:,:,bands].transpose([0,1,3,4,2])

######## Load VAE
encoder, decoder = model.vae_model(latent_dim, len(bands))

######## Build the VAE
vae, vae_utils, Dkl = vae_functions.build_vanilla_vae(encoder, decoder, full_cov=False, coeff_KL = 0)

######## Comment or not depending on what's necessary
# Load weights
#vae, vae_utils, encoder, Dkl = utils.load_vae_conv(path_output, len(bands), folder=True) 
#K.set_value(alpha, utils.load_alpha('/sps/lsst/users/barcelin/weights/LSST/VAE/noisy/v10/'))

print(vae.summary())

######## Define the loss function
alpha = K.variable(1e-2)

def vae_loss(x, x_decoded_mean):
    xent_loss = K.mean(K.sum(K.binary_crossentropy(x, x_decoded_mean), axis=[1,2,3]))
    kl_loss = K.get_value(alpha) * Dkl
    return xent_loss + K.mean(kl_loss)


######## Compile the VAE
vae.compile('adam', loss=vae_loss, metrics=['mse'])

######## Fix the maximum learning rate in adam
K.set_value(vae.optimizer.lr, 0.0001)


#######
# Callback
path_weights = '/sps/lsst/users/barcelin/weights/LSST/VAE/noisy/v16/'
path_plots = '/sps/lsst/users/barcelin/callbacks/LSST/VAE/noisy/v16/'
path_tb = '/sps/lsst/users/barcelin/Graph/vae_lsst_r_band/noisy/'

alphaChanger = changeAlpha(alpha, vae, vae_loss, path_output)# path_weights)
# Callback to display evolution of training
vae_hist = vae_functions.VAEHistory(x_val[:500], vae_utils, latent_dim, alpha, plot_bands=[1,2,3], figroot=path_plots, period=5)
# Keras Callbacks
#earlystop = tf.keras.callbacks.EarlyStopping(monitor='val_mean_squared_error', min_delta=0.0000001, patience=10, verbose=0, mode='min', baseline=None)
checkpointer_mse = ModelCheckpoint(filepath=path_weights+'mse/weights_mse_noisy_v4.{epoch:02d}-{val_mean_squared_error:.2f}.ckpt', monitor='val_mean_squared_error', verbose=1, save_best_only=True,save_weights_only=True, mode='min', period=1)
checkpointer_loss = ModelCheckpoint(filepath=path_weights+'loss/weights_loss_noisy_v4.{epoch:02d}-{val_loss:.2f}.ckpt', monitor='val_loss', verbose=1, save_best_only=True, save_weights_only=True, mode='min', period=1)

######## Define all used callbacks
callbacks = [checkpointer_mse, checkpointer_loss, vae_hist]#, ReduceLROnPlateau(), TerminateOnNaN()]# checkpointer_mse earlystop, checkpointer_loss,vae_hist,, alphaChanger

######## Create generators
#list_of_samples = [x for x in utils.listdir_fullpath(os.path.join(images_dir,'training')) if x.endswith('.npy')]
#list_of_samples_val = [x for x in utils.listdir_fullpath(os.path.join(images_dir,'validation')) if x.endswith('.npy')]

#list_of_samples=['/sps/lsst/users/barcelin/data/single/PSF_lsst_O.65/independant/images_cropped_1.npy',
                  #'/sps/lsst/users/barcelin/data/single/PSF_lsst_O.65/independant/images_cropped_2.npy',
                  #'/sps/lsst/users/barcelin/data/single/PSF_lsst_O.65/independant/images_cropped_3.npy',
                  #'/sps/lsst/users/barcelin/data/single/PSF_lsst_O.65/independant/images_cropped_4.npy'#,
                  #'/sps/lsst/users/barcelin/data/single/PSF_lsst_O.65/independant/images_cropped_5.npy',
                  #'/sps/lsst/users/barcelin/data/single/PSF_lsst_O.65/independant/images_cropped_6.npy',
                  #'/sps/lsst/users/barcelin/data/single/PSF_lsst_O.65/independant/images_cropped_7.npy'#,
#                ]

#list_of_samples_val = ['/sps/lsst/users/barcelin/data/single/PSF_lsst_O.65/independant/images_cropped_val.npy']


#list_of_weights_e_training = ['/sps/lsst/users/barcelin/data/single/PSF_lsst_O.65/independant/e_beta_1.npy',
                    #'/sps/lsst/users/barcelin/data/single/PSF_lsst_O.65/independant/e_beta_2.npy',
                    #'/sps/lsst/users/barcelin/data/single/PSF_lsst_O.65/independant/e_beta_3.npy',
                    #'/sps/lsst/users/barcelin/data/single/PSF_lsst_O.65/independant/e_beta_4.npy'#,
                    #'/sps/lsst/users/barcelin/data/single/PSF_lsst_O.65/independant/e_beta_5.npy',
                    #'/sps/lsst/users/barcelin/data/single/PSF_lsst_O.65/independant/e_beta_6.npy',
                    #'/sps/lsst/users/barcelin/data/single/PSF_lsst_O.65/independant/e_beta_7.npy'
#                    ]

#list_of_weights_e_val = ['/sps/lsst/users/barcelin/data/single/PSF_lsst_O.65/independant/e_beta_val.npy']

images_dir = '/sps/lsst/users/barcelin/data/single_galaxies/'
list_of_samples = [x for x in utils.listdir_fullpath(os.path.join(images_dir,'training')) if x.endswith('.npy')]
list_of_samples_val = [x for x in utils.listdir_fullpath(os.path.join(images_dir,'validation')) if x.endswith('.npy')]



training_generator = generator.BatchGenerator(bands, list_of_samples, total_sample_size=None,
                                    batch_size=batch_size, 
                                    trainval_or_test='training',
                                    do_norm=False,
                                    denorm = False,
                                    list_of_weights_e=None)#180000

validation_generator = generator.BatchGenerator(bands, list_of_samples_val, total_sample_size=None,
                                    batch_size=batch_size, 
                                    trainval_or_test='validation',
                                    do_norm=False,
                                    denorm = False,
                                    list_of_weights_e= None)#180000

######## Train the network
hist = vae.fit_generator(generator=training_generator, epochs=epochs,
                  steps_per_epoch=128,
                  verbose=2,
                  shuffle=True,
                  validation_data=validation_generator,
                  validation_steps=2,
                  callbacks=callbacks,
                  workers=0)
