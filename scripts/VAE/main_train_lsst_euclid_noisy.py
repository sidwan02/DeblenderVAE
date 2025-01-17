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

sys.path.insert(0,'../tools_for_VAE/')
from tools_for_VAE import model, vae_functions, utils, generator
from tools_for_VAE.callbacks import changeAlpha

print(sys.argv)

cur_dir = os.path.dirname(os.path.abspath(__file__))
proj_dir = os.path.dirname(os.path.dirname(cur_dir))

print("proj_dir: ", proj_dir)

######## Set some parameters
batch_size = 100
latent_dim = 32
epochs = int(sys.argv[4])
load = str(sys.argv[5]).lower() == 'true'
bands = [0,1,2,3,4,5,6,7,8,9]

# python main_train_lsst_euclid_noisy.py <ADAM LR> <IMAGES_DIR NAME> <PATH_WEIGHTS/PLOTS NAME> <EPOCHS> <LOAD?> <PATH_OUTPUT NAME>

# python main_train_lsst_euclid_noisy.py 0.01 blah1 blah2 1 false blah3

images_dir = proj_dir + '/data/isolated_galaxies/'+str(sys.argv[2])+'validation/'
path_output = proj_dir + '/weights/LSST_EUCLID/VAE/noisy/'+str(sys.argv[6])

######## Import data for callback (Only if VAEHistory is used)
x_val = np.load(os.path.join(images_dir, 'galaxies_isolated_20191024_0_images.npy'))[:500,:,bands].transpose([0,1,3,4,2])

######## Load VAE
encoder, decoder = model.vae_model(latent_dim, len(bands))

######## Build the VAE
if not load:
    vae, vae_utils, Dkl = vae_functions.build_vanilla_vae(encoder, decoder, full_cov=False, coeff_KL = 0)
else:
    vae, vae_utils, encoder, Dkl = utils.load_vae_conv(path_output, len(bands), folder=True) 

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
K.set_value(vae.optimizer.lr, sys.argv[1])


#######
# Callback
path_weights = proj_dir + '/weights/LSST_EUCLID/VAE/noisy/'+ str(sys.argv[3])
path_plots = proj_dir + '/callbacks/LSST_EUCLID/VAE/noisy/'+ str(sys.argv[3])

# Callback to display evolution of training
vae_hist = vae_functions.VAEHistory(x_val[:500], vae_utils, latent_dim, alpha, plot_bands=[5,6,7], figroot=os.path.join(path_plots, 'test_noisy_LSST_v4'), period=2)
# Keras Callbacks
checkpointer_mse = ModelCheckpoint(filepath=os.path.join(path_weights, 'mse/weights_mse_noisy_v4.{epoch:02d}-{val_mean_squared_error:.2f}.ckpt'), monitor='val_mean_squared_error', verbose=1, save_best_only=True,save_weights_only=True, mode='min', period=1)
checkpointer_loss = ModelCheckpoint(filepath=os.path.join(path_weights,'loss/weights_loss_noisy_v4.{epoch:02d}-{val_loss:.2f}.ckpt'), monitor='val_loss', verbose=1, save_best_only=True, save_weights_only=True, mode='min', period=1)

######## Define all used callbacks
callbacks = [checkpointer_mse, checkpointer_loss, vae_hist]# checkpointer_mse earlystop, checkpointer_loss,vae_hist,, alphaChanger

######## Create generators
images_dir = proj_dir + '/data/isolated_galaxies/'+str(sys.argv[2])
list_of_samples = [x for x in utils.listdir_fullpath(os.path.join(images_dir,'training')) if x.endswith('.npy')]
list_of_samples_val = [x for x in utils.listdir_fullpath(os.path.join(images_dir,'validation')) if x.endswith('.npy')]


training_generator = generator.BatchGenerator(bands, list_of_samples, total_sample_size=None,
                                    batch_size=batch_size, 
                                    trainval_or_test='training',
                                    do_norm=False,
                                    denorm = False,
                                    path = os.path.join(images_dir, "test/"),
                                    list_of_weights_e= None)

validation_generator = generator.BatchGenerator(bands, list_of_samples_val, total_sample_size=None,
                                    batch_size=batch_size, 
                                    trainval_or_test='validation',
                                    do_norm=False,
                                    denorm = False,
                                    path = os.path.join(images_dir, "test/"),
                                    list_of_weights_e= None)

######## Train the network
hist = vae.fit_generator(generator=training_generator, epochs=epochs,
                  steps_per_epoch=128,
                  verbose=2,
                  shuffle=True,
                  validation_data=validation_generator,
                  validation_steps=16,
                  callbacks=callbacks,
                  workers=0,
                  use_multiprocessing = True)
