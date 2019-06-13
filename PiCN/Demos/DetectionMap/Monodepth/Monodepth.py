"""
This is a simplified version of the code in monodepth_simple.py from https://github.com/mrharicot/monodepth.
"""

import os

from PiCN.definitions import ROOT_DIR
from PIL import Image
from PiCN.Demos.DetectionMap.Monodepth.MonodepthModel import *

def get_disparity_map(image, model_path: str= "Demos/DetectionMap/Monodepth/Model/model_cityscapes/model_cityscapes"):
    """
    Get the disparity map from an input image.
    The input image is assumed to be the left image of a stereo image.

    :param image: The image which is to estimate the corresponding right image
    :param model_path: The path to the model used for the creation of the disparity map
    :return: The disparity map
    """
    tf.reset_default_graph()
    original_height, original_width = image.shape[:2]
    model_path = os.path.join(ROOT_DIR, model_path)

    params = monodepth_parameters(
        encoder="vgg",
        height=256,
        width=512,
        batch_size=2,
        num_threads=8,
        num_epochs=1,
        do_stereo=False,
        wrap_mode="border",
        use_deconv=False,
        alpha_image_loss=0,
        disp_gradient_loss_weight=0,
        lr_loss_weight=0,
        full_summary=False)

    left = tf.placeholder(tf.float32, [2, 256, 512, 3])
    model = MonodepthModel(params, "test", left, None, tf.AUTO_REUSE)

    config = tf.ConfigProto(allow_soft_placement=True)
    sess = tf.Session(config=config)

    train_saver = tf.train.Saver()
    restore_path = model_path.split(".")[0]
    train_saver.restore(sess, restore_path)

    image = np.array(Image.fromarray(image).resize((512, 256)))
    image = image.astype(np.float32) / 255
    images = np.stack((image, np.fliplr(image)), 0)
    disparity_map = sess.run(model.disp_left_est[0], feed_dict={left: images})
    disparity_map_pp = post_process_disparity(disparity_map.squeeze()).astype(np.float32)
    disparity_map_pp = np.array(Image.fromarray(disparity_map_pp.squeeze()).resize((original_width, original_height)))
    return disparity_map_pp

def post_process_disparity(disparity_map):
    """
    Post processe the disparity map in order to be able to convert it to an image.

    :param disparity_map: The unprocessed disparity
    :return: The processed disparity map
    """
    _, h, w = disparity_map.shape
    l_disp = disparity_map[0, :, :]
    r_disp = np.fliplr(disparity_map[1, :, :])
    m_disp = 0.5 * (l_disp + r_disp)
    l, _ = np.meshgrid(np.linspace(0, 1, w), np.linspace(0, 1, h))
    l_mask = 1.0 - np.clip(20 * (l - 0.05), 0, 1)
    r_mask = np.fliplr(l_mask)
    return r_mask * l_disp + l_mask * r_disp + (1.0 - l_mask - r_mask) * m_disp
