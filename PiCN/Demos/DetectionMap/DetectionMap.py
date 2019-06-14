import os
import matplotlib.pyplot as plt

from pygeodesy.ellipsoidalVincenty import LatLon
from PiCN.definitions import ROOT_DIR
from PiCN.Demos.DetectionMap.DetectionMapObject import *
from PiCN.Demos.DetectionMap.Gmplot import gmplot
from PiCN.Demos.DetectionMap.Monodepth.MonodepthModel import *
from PiCN.Demos.DetectionMap.Monodepth.Monodepth import get_disparity_map

from PiCN.Demos.DetectionMap.YOLO.ObjectDetection import detect_objects

class DetectedObjectGPS:

    def __init__(self, focal_length=2262, baseline=0.22, training_width=2048):
        # values from the cityscapes dataset
        self.focal_length = focal_length
        self.basline = baseline
        self.training_width = training_width

        self.classified_map_detections = []


    def run(self, start_point: LatLon, start_bearing, image, scaling_factor: int=1, id: int=0):
        """
        Create the disparity map, run the object detection algorithm and calculate the GPS-coordinates of the
        classified objects using the disparity map.

        :param start_point: LatLon object (latitude, longitude) of the position of the camera (car)
        :param start_bearing: The viewing direction of the camera as the deviation from north in degrees
        :param image: The input image
        :param focal_length: The focal length of the camera being used to shoot the image
        :return: The GPS-coordinates of the classified objects
        """

        print("Calculating depth map...")
        disparity_map = get_disparity_map(image)
        print("Detecting objects...")
        detections, self.colors = detect_objects(image, id)
        gps = self.get_gps_of_detected_objects(image, start_point, start_bearing, disparity_map, detections, scaling_factor)
        return gps

    def get_gps_of_detected_objects(self, image, position: LatLon, start_bearing, disparity_map, detections, scaling_factor):
        """
        Use the GPS coordinates of the camera (car) and the disparity map to calculate the GPS coordinates of the
        detected objects.

        :param image: The input image
        :param position: LatLon object (latitude, longitude) of the position of the camera (car)
        :param start_bearing: The viewing direction of the camera as the deviation from north in degrees
        :param disparity_map: The disparity map as an image
        :param detections: List of dicts containing the name and the x, y-coordinates of the classified objects
        :param scaling_factor: A factor which scales x and z distances
        :return: The GPS-coordinates of the detected objects
        """
        original_width = image.shape[1]
        gps = []
        for detection in detections:
            u, v = detection["coords"]
            z = self.basline * self.focal_length / (disparity_map[v, u] * self.training_width)
            z *= scaling_factor
            x = (u - original_width / 2) * z / (original_width / self.training_width) / self.focal_length
            distance, bearing = self.xz_to_dist_bearing(x, z, start_bearing)
            new_gps = position.destination(distance, bearing)
            gps.append(new_gps)
            self.classified_map_detections.append((detection.get("id"), new_gps.lat, new_gps.lon))
        return gps

    def xz_to_dist_bearing(self, x, z, b):
        dist = np.hypot(x, z)
        bearing = (b + np.rad2deg(np.arctan(x / z))) % 360
        return dist, bearing

    def gps_to_global_xz(self, start_point: LatLon, start_bearing, gps):
        """
        In order to plot the detected objects in relation to one camera, we need to translate GPS-coordinates
        to x, z-coordinates using one camera as the zero point.

        :param start_point: LatLon object (latitude, longitude) of the camera defined as the zero point
        :param start_bearing: The deviation from north in degrees, determines to direction of the z axis
        :param gps: List of GPS-coordinates
        :return: The calculated x and z values
        """
        x_list, z_list = [], []
        for coord in gps:
            dist, bearing, _ = start_point.distanceTo3(coord)
            bearing_diff = (start_bearing - bearing)
            x = -np.sin(np.deg2rad(bearing_diff)) * dist
            z = np.cos(np.deg2rad(bearing_diff)) * dist
            x_list.append(x), z_list.append(z)
        return x_list, z_list

    def create_map(self, start_lat, start_lon, id: int=0):
        """
        Create a map using gmplot and a Google API-key stored in "Demos/DetectionMap/Assets/api_key.txt".
        Each detected object is printed on the map as a red dot.

        :param start_lat: The latitude of the center of the view
        :param start_lon: The lonitude of the center of the view
        :param id: Optional parameter for saving multiple maps under different names
        """
        f = open(os.path.join(ROOT_DIR, "Demos/DetectionMap/Assets/api_key.txt"))
        api_key = f.read()
        f.close()

        gmap = gmplot.GoogleMapPlotter(start_lat, start_lon, 19, apikey=api_key)
        gmap.marker(start_lat, start_lon, "Position")

        for object in self.classified_map_detections:
            class_id = object[0]
            rgb = [int(c) for c in self.colors[class_id]]
            color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            lat, lon = object[1:3]
            gmap.scatter([lat], [lon], color, size=1.5, marker=False)

        # Make sure the given folder exists, if not create it
        if not os.path.exists(os.path.join(ROOT_DIR, "Demos/DetectionMap/Assets/Maps")):
            os.makedirs(os.path.join(ROOT_DIR, "Demos/DetectionMap/Assets/Maps"))

        gmap.draw(os.path.join(ROOT_DIR, f"Demos/DetectionMap/Assets/Maps/map{id}.html"))

    def plot_data(self, x, z, id: int=0, range_x: int=None, range_y: int=None):
        """
        Simple plot function to plot points on a grid with equal proportions

        :param x: List of x-values
        :param z: List of z-values
        """
        plt.figure()
        for i, x_i, z_i in zip(range(len(x)+1), x, z):
            class_id = self.classified_map_detections[i][0]
            rgb = [int(c) for c in self.colors[class_id]]
            color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            plt.plot(x_i, z_i, color, marker="o")

        if not range_x:
            range_x = np.max(np.abs(x)) + 10
        if not range_y:
            range_y = np.max(np.abs(z)) + 10
        # plt.ylim(np.min([np.min(z)-10, 0]), range_y)
        plt.ylim(0, range_y)
        plt.xlim(-range_x, range_x)
        plt.gca().set_aspect("equal", adjustable="box")
        plt.title(f"Detections in bird's-eye view")
        plt.xlabel("x (in meters)")
        plt.ylabel("z (in meters)")

        # Make sure the given folder exists, if not create it
        if not os.path.exists(os.path.join(ROOT_DIR, f"Demos/DetectionMap/Assets/Plots")):
            os.makedirs(os.path.join(ROOT_DIR, f"Demos/DetectionMap/Assets/Plots"))

        plt.savefig(os.path.join(ROOT_DIR, f"Demos/DetectionMap/Assets/Plots/plot{id}.jpg"))
        plt.close()

def detection_map(map_det_obj_str: str, build_map: int, id: int):
    """
    Detection map function for a single image.

    :param map_det_obj_str: String representing a MapDetectionObj
    :param build_map: Determines if a map is created. Pass 1 if a map should be created, 0 otherwise.
    :return: Dict containing the names and the GPS-coordinates of all detected object
    """
    map_det_obj = DetectionMapObject.from_string(map_det_obj_str)
    image, lat, lon, start_bearing, scaling_factor = map_det_obj.unpack()
    start_point = LatLon(lat, lon)

    d = DetectedObjectGPS()
    gps = d.run(start_point, start_bearing, image, scaling_factor, id)

    x, z = d.gps_to_global_xz(start_point, start_bearing, gps)
    d.plot_data(x, z, id)

    if build_map:
        d.create_map(lat, lon, id)
    return d.classified_map_detections

def detection_map_2(map_det_obj_str1: str, map_det_obj_str2: str, build_map: bool):
    """
    Detection map function for two images.

    :param map_det_obj_str1: String representing first MapDetectionObj. This one is used as zero point.
    :param map_det_obj_str2: String representing a second MapDetectionObj
    :param build_map: Pass 1 if a map should be created, 0 otherwise (booleans are not supported yet)
    :return: Dict containing the names and the GPS-coordinates of all detected object
    """
    # image from car 1
    map_det_obj1 = DetectionMapObject.from_string(map_det_obj_str1)
    image1, lat1, lon1, start_bearing1, scaling_factor1 = map_det_obj1.unpack()
    start_point1 = LatLon(lat1, lon1)

    # image from car 2
    map_det_obj2 = DetectionMapObject.from_string(map_det_obj_str2)
    image2, lat2, lon2, start_bearing2, scaling_factor2 = map_det_obj2.unpack()
    start_point2 = LatLon(lat2, lon2)

    d = DetectedObjectGPS()
    gps = d.run(start_point1, start_bearing1, image1, scaling_factor1, 0)
    gps += d.run(start_point2, start_bearing2, image2, scaling_factor2, 1)

    x, z = d.gps_to_global_xz(start_point1, start_bearing1, gps)
    d.plot_data(x, z)

    if build_map:
        d.create_map(lat1, lon1)

    return d.classified_map_detections


# def map_detection_video(map_det_obj_str: str, build_map: int, id: int):
#     """
#     Map detection function for a single image.
#
#     :param map_det_obj_str: String representing a MapDetectionObj
#     :param build_map: Pass 1 if a map should be created, 0 otherwise (booleans are not supported yet)
#     :return: Dict containing the names and the GPS-coordinates of all detected object
#     """
#     map_det_obj = DetectionMapObject.from_string(map_det_obj_str)
#     image, lat, lon, start_bearing, scaling_factor = map_det_obj.unpack()
#     start_point = LatLon(lat, lon)
#
#     d = DetectedObjectGPS()
#     gps = d.run(start_point, start_bearing, image, scaling_factor, id)
#
#     x, z = d.gps_to_global_xz(start_point, start_bearing, gps)
#     d.plot_data(x, z, id, 40, 80)
#
#     if build_map:
#         d.create_map(lat, lon, id)
#
#     return d.classified_map_detections