import torch
from torch.autograd import Variable
import math
import numpy as np
from src.box_utils import nms, _preprocess, _preprocess_batch
import cv2


def run_first_stage_parallel_half(image, net, scale_list, threshold, device):
    """Run P-Net, generate bounding boxes, and do NMS.

    Arguments:
        image: an instance of PIL.Image.
        net: an instance of pytorch's nn.Module, P-Net.
        scale: a float number,
            scale width and height of the image by this number.
        threshold: a float number,
            threshold on the probability of a face when generating
            bounding boxes from predictions of the net.

    Returns:
        a float numpy array of shape [n_boxes, 9],
            bounding boxes with scores and offsets (4 + 1 + 4).
    """

    # scale the image and convert it to a float array
    # width, height = image.size
    scale = np.array(scale_list)
    height, width, _ = image.shape
    sw = np.ceil(width*scale).astype(int)
    sh = np.ceil(height*scale).astype(int)
    # img = image.resize((sw, sh), Image.BILINEAR)

    img_batch = np.zeros(shape=(len(scale_list),sh[0],sw[0],3))
    img = cv2.resize(image, (sw[0], sh[0]))
    img = np.asarray(img, 'float32')
    img_batch[0, :, :, :] = img
    im1 = img
    for i in range(1,len(scale_list)):
        im1 = im1[::2,::2,:]
        img_batch[i, 0:sh[i], 0:sw[i], :] = im1

    with torch.no_grad():
        img = Variable(torch.FloatTensor(_preprocess_batch(img_batch)).to(device))
        output = net(img)

    temp = output[1].cpu()
    probs = temp.data.numpy()[:, 1, :, :]
    offsets = output[0].cpu().data.numpy()
    # probs: probability of a face at each sliding window
    # offsets: transformations to true bounding boxes

    bboxes = []
    for k,scale in enumerate(scale_list):
        boxes = _generate_bboxes(probs[k], np.expand_dims(offsets[k], 0), scale, threshold)
        if len(boxes) == 0:
            continue

        keep = nms(boxes[:, 0:5], overlap_threshold=0.5)
        bboxes.append(boxes[keep])
    return bboxes


def _generate_bboxes(probs, offsets, scale, threshold):
    """Generate bounding boxes at places
    where there is probably a face.

    Arguments:
        probs: a float numpy array of shape [n, m].
        offsets: a float numpy array of shape [1, 4, n, m].
        scale: a float number,
            width and height of the image were scaled by this number.
        threshold: a float number.

    Returns:
        a float numpy array of shape [n_boxes, 9]
    """

    # applying P-Net is equivalent, in some sense, to
    # moving 12x12 window with stride 2
    stride = 2
    cell_size = 12

    # indices of boxes where there is probably a face
    inds = np.where(probs > threshold)

    if inds[0].size == 0:
        return np.array([])

    # transformations of bounding boxes
    tx1, ty1, tx2, ty2 = [offsets[0, i, inds[0], inds[1]] for i in range(4)]
    # they are defined as:
    # w = x2 - x1 + 1
    # h = y2 - y1 + 1
    # x1_true = x1 + tx1*w
    # x2_true = x2 + tx2*w
    # y1_true = y1 + ty1*h
    # y2_true = y2 + ty2*h

    offsets = np.array([tx1, ty1, tx2, ty2])
    score = probs[inds[0], inds[1]]

    # P-Net is applied to scaled images
    # so we need to rescale bounding boxes back
    bounding_boxes = np.vstack([
        np.round((stride*inds[1] + 1.0)/scale),
        np.round((stride*inds[0] + 1.0)/scale),
        np.round((stride*inds[1] + 1.0 + cell_size)/scale),
        np.round((stride*inds[0] + 1.0 + cell_size)/scale),
        score, offsets
    ])
    # why one is added?

    return bounding_boxes.T
