import io
import os
import zipfile

import matplotlib.pyplot as plt
import requests

from PiCN.definitions import ROOT_DIR
from PiCN.Demos.DetectionMap.DetectionMapObject import *
from PiCN.Demos.DetectionMap.Monodepth.MonodepthModel import *

def detect_objects(image, id: int=0):
    """
    Detect objects and classify them.
    The model being used is YOLOv3, while only labels in "/Demos/DetectionMap/Model/labels_inculded" are considered.

    :param image: The input image
    :return: List of dicts containing the name and the x, y-coordinates of the classified objects
    """
    # Check if model exists. If not it gets downloaded from github
    model_path = os.path.join(ROOT_DIR, "Demos/DetectionMap/YOLO/Model")

    if not os.path.exists(model_path):
        print("Model for object detection not found. \nDownloading from GitHub...")
        path = os.path.join(ROOT_DIR, "Demos/DetectionMap/YOLO")
        url = "https://github.com/cn-uofbasel/PiCN/releases/download/0.0.1/YOLO.zip"

        response = requests.get(url)
        print("Download done!")
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            for info in zf.infolist():
                zf.extract(info, path)

    labels_file = open(os.path.join(model_path, "labels"))
    labels = labels_file.read().strip().split("\n")
    labels_file.close()

    labels_include_file = open(os.path.join(model_path, "labels_included"))
    labels_include = labels_include_file.read().strip().split("\n")
    labels_include_file.close()

    np.random.seed(42)
    colors = np.random.randint(0, 255, size=(len(labels), 3),
                               dtype="uint8")

    config_path = os.path.join(model_path, "yolov3.cfg")
    weights_path = os.path.join(model_path, "yolov3.weights")
    net = cv2.dnn.readNetFromDarknet(config_path, weights_path)
    ln = net.getLayerNames()
    ln = [ln[i[0] - 1] for i in net.getUnconnectedOutLayers()]
    
    original_height, original_width = image.shape[:2]
    blob = cv2.dnn.blobFromImage(image, 1 / 255.0, (416, 416), swapRB=True, crop=False)
    net.setInput(blob)
    layer_outputs = net.forward(ln)
    detections = []
    boxes = []
    confidences = []
    class_ids = []

    for output in layer_outputs:
        for detection in output:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            name = labels[int(class_id)]
            if confidence > 0.5 and name in labels_include:
                box = detection[0:4] * np.array([original_width, original_height,
                                                 original_width, original_height])
                (x, y, width, height) = box.astype("int")
                detections.append({"id": int(class_id), "coords": (x,y)})

                x = int(x - (width / 2))
                y = int(y - (height / 2))
                boxes.append([x, y, int(width), int(height)])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    # draw bounding boxes around classified objects
    idxs = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.3)
    if len(idxs) > 0:
        for i in idxs.flatten():
            # extract the bounding box coordinates
            (x, y) = (boxes[i][0], boxes[i][1])
            (w, h) = (boxes[i][2], boxes[i][3])
            # draw a bounding box rectangle and label on the image
            color = [int(c) for c in colors[class_ids[i]]]
            cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
            # text = "{}: {:.4f}".format(labels[int(class_ids[i])], confidences[i])
            # cv2.putText(image, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX,
            #             0.5, color, 2)

    # Make sure the given folder exists, if not create it
    if not os.path.exists(os.path.join(ROOT_DIR, "Demos/DetectionMap/Assets/Classified")):
        os.makedirs(os.path.join(ROOT_DIR, "Demos/DetectionMap/Assets/Classified"))

    plt.imsave(os.path.join(ROOT_DIR, f"Demos/DetectionMap/Assets/Classified/classified{id}.jpg"), image)

    return [detections[i] for i in idxs.flatten()], colors
