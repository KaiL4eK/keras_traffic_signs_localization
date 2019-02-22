#! /usr/bin/env python

import os
import json
import cv2
from utils.utils import get_yolo_boxes, makedirs, init_session
from utils.bbox import draw_boxes
from keras.models import load_model
from tqdm import tqdm
import numpy as np
import time

import argparse
argparser = argparse.ArgumentParser(description='Predict with a trained yolo model')
argparser.add_argument('-c', '--conf', help='path to configuration file')
argparser.add_argument('-i', '--input', help='path to an image, a directory of images, a video, or webcam')
argparser.add_argument('-w', '--weights', help='weights path')
argparser.add_argument('-o', '--output', default='output/', help='path to output directory')

args = argparser.parse_args()


def _main_():
    config_path  = args.conf
    input_path   = args.input
    output_path  = args.output
    weights_path = args.weights

    with open(config_path) as config_buffer:    
        config = json.load(config_buffer)

    makedirs(output_path)

    config['model']['labels'] = ['brick', 'forward', 'forward and left', 'forward and right', 'left', 'right']

    ###############################
    #   Set some parameter
    ###############################

    net_h, net_w = config['model']['infer_shape']
    obj_thresh, nms_thresh = 0.5, 0.45

    ###############################
    #   Load the model
    ###############################

    os.environ['CUDA_VISIBLE_DEVICES'] = config['train']['gpus']
    infer_model = load_model(weights_path)

    ###############################
    #   Predict bounding boxes 
    ###############################

    if 'webcam' in input_path: # do detection on the first webcam
        video_reader = cv2.VideoCapture(0)

        # the main loop
        batch_size  = 1
        images      = []
        while True:
            ret_val, image = video_reader.read()
            if ret_val == True: images += [image]

            if (len(images)==batch_size) or (ret_val==False and len(images)>0):
                batch_boxes = get_yolo_boxes(infer_model, images, net_h, net_w, config['model']['anchors'], obj_thresh, nms_thresh)

                for i in range(len(images)):
                    draw_boxes(images[i], batch_boxes[i], config['model']['labels'], obj_thresh) 
                    cv2.imshow('video with bboxes', images[i])
                images = []
            if cv2.waitKey(1) == 27: 
                break  # esc to quit
        cv2.destroyAllWindows()        
    elif input_path[-4:] == '.mp4' or input_path[-5:] == '.webm': # do detection on a video  
        video_out = output_path + os.path.basename(input_path.split('.')[0] + '.mp4')
        video_reader = cv2.VideoCapture(input_path)

        nb_frames = int(video_reader.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_h = int(video_reader.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_w = int(video_reader.get(cv2.CAP_PROP_FRAME_WIDTH))

        video_writer = cv2.VideoWriter(video_out,
                               cv2.VideoWriter_fourcc(*'MPEG'),
                               25.0,
                               (frame_w, frame_h))
        # the main loop
        batch_size  = 1
        images      = []
        start_point = 0 #%
        show_window = False
        for i in tqdm(range(nb_frames)):
            _, image = video_reader.read()

            if (float(i+1)/nb_frames) > start_point/100.:
                images += [image]

                if (i%batch_size == 0) or (i == (nb_frames-1) and len(images) > 0):
                    # predict the bounding boxes
                    batch_boxes = get_yolo_boxes(infer_model, images, net_h, net_w, config['model']['anchors'], obj_thresh, nms_thresh)

                    for i in range(len(images)):
                        # draw bounding boxes on the image using labels
                        draw_boxes(images[i], batch_boxes[i], config['model']['labels'], obj_thresh)   

                        # show the video with detection bounding boxes          
                        if show_window: cv2.imshow('video with bboxes', images[i])  

                        # write result to the output video
                        video_writer.write(images[i]) 
                    images = []
                if show_window and cv2.waitKey(1) == 27: break  # esc to quit

        if show_window: cv2.destroyAllWindows()
        video_reader.release()
        video_writer.release()       
    else: # do detection on an image or a set of images
        image_paths = []

        if os.path.isdir(input_path): 
            for inp_file in os.listdir(input_path):
                image_paths += [os.path.join(input_path, inp_file)]
        else:
            image_paths += [input_path]

        image_paths = [inp_file for inp_file in image_paths if (inp_file[-4:] in ['.jpg', '.png', 'JPEG', '.ppm'])]

        processing_count = 0
        sum_time = 0

        # the main loop
        for image_path in tqdm(image_paths):
            image = cv2.imread(image_path)
            # print(image_path)

            start_time = time.time()

            # predict the bounding boxes
            boxes = get_yolo_boxes(infer_model, [image], net_h, net_w, config['model']['anchors'], obj_thresh, nms_thresh)[0]

            sum_time += time.time() - start_time
            processing_count += 1

            # draw bounding boxes on the image using labels
            draw_boxes(image, boxes, config['model']['labels'], obj_thresh) 

            cv2.imshow('1', image)
            cv2.waitKey(0)
            # write the image with bounding boxes to file
            # cv2.imwrite(output_path + image_path.split('/')[-1], np.uint8(image))         

        fps = processing_count / sum_time
        print('Result: {}'.format(fps))

if __name__ == '__main__':
    _main_()
